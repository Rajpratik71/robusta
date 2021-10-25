import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from hikaru.model import Node, DaemonSet

from ...core.reporting import (
    Finding,
    FindingSubjectType,
    FindingSubject,
    FindingSeverity,
    FindingSource,
)
from ...core.model.events import ExecutionBaseEvent
from ..kubernetes.custom_models import RobustaPod, RobustaDeployment, RobustaJob

SEVERITY_MAP = {
    "critical": FindingSeverity.HIGH,
    "error": FindingSeverity.MEDIUM,
    "warning": FindingSeverity.LOW,
    "info": FindingSeverity.INFO,
}


# for parsing incoming data
class PrometheusAlert(BaseModel):
    endsAt: datetime
    generatorURL: str
    startsAt: datetime
    fingerprint: Optional[str] = ""
    status: str
    labels: Dict[Any, Any]
    annotations: Dict[Any, Any]


# for parsing incoming data
class AlertManagerEvent(BaseModel):
    alerts: List[PrometheusAlert] = []
    externalURL: str
    groupKey: str
    version: str
    commonAnnotations: Optional[Dict[Any, Any]] = None
    commonLabels: Optional[Dict[Any, Any]] = None
    groupLabels: Optional[Dict[Any, Any]] = None
    receiver: str
    status: str


# everything here needs to be optional due to annoying subtleties regarding dataclass inheritance
# see explanation in the code for BaseEvent
@dataclass
class PrometheusKubernetesAlert(ExecutionBaseEvent):
    alert: Optional[PrometheusAlert] = None
    alert_name: Optional[str] = None
    alert_severity: Optional[str] = None
    node: Optional[Node] = None
    pod: Optional[RobustaPod] = None
    deployment: Optional[RobustaDeployment] = None
    job: Optional[RobustaJob] = None
    daemonset: Optional[DaemonSet] = None

    def get_title(self) -> str:
        annotations = self.alert.annotations
        if annotations.get("summary"):
            return f'{annotations["summary"]}'
        else:
            return self.alert.labels.get("alertname", "")

    def get_description(self) -> str:
        annotations = self.alert.annotations
        clean_description = ""
        if annotations.get("description"):
            # remove "LABELS = map[...]" from the description as we already add a TableBlock with labels
            clean_description = re.sub(
                r"LABELS = map\[.*\]$", "", annotations["description"]
            )
        return clean_description

    def __get_alert_subject(self) -> FindingSubject:
        subject_type: FindingSubjectType = FindingSubjectType.TYPE_NONE
        name: Optional[str] = None
        namespace: Optional[str] = None

        if self.pod:
            subject_type = FindingSubjectType.TYPE_POD
            name = self.pod.metadata.name
            namespace = self.pod.metadata.namespace
        elif self.job:
            subject_type = FindingSubjectType.TYPE_JOB
            name = self.job.metadata.name
            namespace = self.job.metadata.namespace
        elif self.deployment:
            subject_type = FindingSubjectType.TYPE_DEPLOYMENT
            name = self.deployment.metadata.name
            namespace = self.deployment.metadata.namespace
        elif self.daemonset:
            subject_type = FindingSubjectType.TYPE_DAEMONSET
            name = self.daemonset.metadata.name
            namespace = self.daemonset.metadata.namespace
        elif self.node:
            subject_type = FindingSubjectType.TYPE_NODE
            name = self.node.metadata.name

        return FindingSubject(name, subject_type, namespace)

    def create_default_finding(self) -> Finding:
        alert_subject = self.__get_alert_subject()
        return Finding(
            title=self.get_title(),
            description=self.get_description(),
            source=FindingSource.PROMETHEUS,
            aggregation_key=self.alert_name,
            severity=SEVERITY_MAP.get(
                self.alert.labels.get("severity"), FindingSeverity.INFO
            ),
            subject=alert_subject,
        )
