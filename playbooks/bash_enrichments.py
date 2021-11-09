from robusta.api import *


@action
def pod_bash_enricher(event: PodEvent, params: BashParams):
    pod = event.get_pod()
    if not pod:
        logging.error(f"cannot run PodBashEnricher on event with no pod: {event}")
        return

    block_list: List[BaseBlock] = []
    exec_result = pod.exec(params.bash_command)
    block_list.append(MarkdownBlock(f"Command results for *{params.bash_command}:*"))
    block_list.append(MarkdownBlock(exec_result))
    event.add_enrichment(block_list)


@action
def node_bash_enricher(event: NodeEvent, params: BashParams):
    node = event.get_node()
    if not node:
        logging.error(f"cannot run NodeBashEnricher on event with no node: {event}")
        return

    block_list: List[BaseBlock] = []
    exec_result = RobustaPod.exec_in_debugger_pod(
        "node-bash-pod", node.metadata.name, params.bash_command
    )
    block_list.append(MarkdownBlock(f"Command results for *{params.bash_command}:*"))
    block_list.append(MarkdownBlock(exec_result))
    event.add_enrichment(block_list)
