from __future__ import annotations

from dataclasses import replace

from munk.perception.screen_graph import ObservedScreenFrame, TreeNodeSnapshot, VisualElementLink
from munk.perception.types import ClickableElement

from .geometry import box_iou
from .tree_models import ParsedTreeNode, summarize_tree_nodes

STABLE_KEY_GRID_COLUMNS = 8
STABLE_KEY_GRID_ROWS = 16


def build_observed_screen_frame(
    *,
    entry_identity: str | None,
    screen_size: tuple[int, int],
    elements: list[ClickableElement],
    tree_nodes: list[ParsedTreeNode],
    tree_available: bool,
    tree_error: str | None = None,
    keyboard_visible: bool | None = None,
    keyboard_bounds: tuple[int, int, int, int] | None = None,
    keyboard_source: str | None = None,
) -> tuple[list[ClickableElement], ObservedScreenFrame]:
    snapshots = [_to_snapshot(node) for node in tree_nodes]
    snapshots = _with_disambiguated_stable_keys(snapshots, screen_size=screen_size)
    enriched = list(elements)
    links: list[VisualElementLink] = []
    matched_snapshot_indexes: set[int] = set()
    matched_element_indexes: set[int] = set()

    for element_index, element in enumerate(enriched):
        best_index, best_score = _best_tree_match(element, snapshots, matched_snapshot_indexes)
        if best_index is None:
            continue
        snapshot = snapshots[best_index]
        matched_snapshot_indexes.add(best_index)
        matched_element_indexes.add(element_index)
        links.append(
            VisualElementLink(
                element_id=str(element_index),
                tree_node_id=snapshot.node_id,
                score=best_score,
            )
        )
        snapshots[best_index] = replace(
            snapshot,
            matched_visual_ids=[*snapshot.matched_visual_ids, str(element_index)],
        )
        enriched[element_index] = _enrich_element(element, snapshots[best_index])

    frame = ObservedScreenFrame(
        entry_identity=entry_identity,
        screen_size=screen_size,
        tree_available=tree_available,
        tree_summary=summarize_tree_nodes(tree_nodes) if tree_available else "unavailable",
        tree_error=tree_error,
        keyboard_visible=keyboard_visible,
        keyboard_bounds=keyboard_bounds,
        keyboard_source=keyboard_source,
        tree_nodes=snapshots,
        links=links,
    )
    return enriched, frame


def _to_snapshot(node: ParsedTreeNode) -> TreeNodeSnapshot:
    return TreeNodeSnapshot(
        node_id=node.node_id,
        stable_key=_stable_key(node),
        bounds=node.bounds,
        package_name=node.package_name,
        text=node.text,
        content_desc=node.content_desc,
        resource_id=node.resource_id,
        class_name=node.class_name,
        clickable=node.clickable,
        checkable=node.checkable,
        checked=node.checked,
        enabled=node.enabled,
        focused=node.focused,
        selected=node.selected,
        scrollable=node.scrollable,
        semantic_role=node.semantic_role,
    )


def _stable_key(node: ParsedTreeNode) -> str:
    if node.resource_id:
        return f"rid:{node.resource_id}"
    label = (node.text or node.content_desc or "").strip().lower()
    x1, y1, x2, y2 = node.bounds
    bucket = f"{x1//20}:{y1//20}:{x2//20}:{y2//20}"
    class_name = (node.class_name or "unknown").lower()
    flags = f"c{int(node.clickable)}k{int(node.checkable)}s{int(node.scrollable)}"
    if label:
        return f"{class_name}|{label}|{flags}|{bucket}"
    return f"{class_name}|{flags}|{bucket}"


def _with_disambiguated_stable_keys(
    snapshots: list[TreeNodeSnapshot],
    *,
    screen_size: tuple[int, int],
) -> list[TreeNodeSnapshot]:
    resource_id_counts: dict[str, int] = {}
    for snapshot in snapshots:
        if not snapshot.resource_id:
            continue
        resource_id_counts[snapshot.resource_id] = resource_id_counts.get(snapshot.resource_id, 0) + 1

    updated: list[TreeNodeSnapshot] = []
    for snapshot in snapshots:
        resource_id = snapshot.resource_id
        if resource_id is None or resource_id_counts.get(resource_id, 0) <= 1:
            updated.append(snapshot)
            continue
        updated.append(
            replace(
                snapshot,
                stable_key=f"{snapshot.stable_key}|grid:{_grid_position_key(snapshot.bounds, screen_size=screen_size)}",
            )
        )
    return updated


def _grid_position_key(
    bounds: tuple[int, int, int, int],
    *,
    screen_size: tuple[int, int],
) -> str:
    x1, y1, _, _ = bounds
    screen_width = max(1, screen_size[0])
    screen_height = max(1, screen_size[1])
    x_index = _clamp_grid_index(
        int((x1 * STABLE_KEY_GRID_COLUMNS) / screen_width),
        upper_bound=STABLE_KEY_GRID_COLUMNS - 1,
    )
    y_index = _clamp_grid_index(
        int((y1 * STABLE_KEY_GRID_ROWS) / screen_height),
        upper_bound=STABLE_KEY_GRID_ROWS - 1,
    )
    return f"{x_index}:{y_index}"


def _clamp_grid_index(value: int, *, upper_bound: int) -> int:
    return max(0, min(value, upper_bound))


def _best_tree_match(
    element: ClickableElement,
    snapshots: list[TreeNodeSnapshot],
    used_indexes: set[int],
) -> tuple[int | None, float]:
    best_index: int | None = None
    best_score = 0.0
    for index, snapshot in enumerate(snapshots):
        if index in used_indexes:
            continue
        score = _match_score(element, snapshot)
        if score > best_score:
            best_score = score
            best_index = index
    threshold = 0.75 if element.kind == "text" else 0.55
    if best_index is None or best_score < threshold:
        return None, 0.0
    return best_index, best_score


def _match_score(element: ClickableElement, snapshot: TreeNodeSnapshot) -> float:
    iou = box_iou(element.box, snapshot.bounds)
    containment = 1.0 if _center_inside(element.box, snapshot.bounds) else 0.0
    text_similarity = _text_similarity(element.text, snapshot.text or snapshot.content_desc)
    clickable_bonus = 0.15 if snapshot.clickable else 0.0
    distance_penalty = _normalized_center_distance(element.box, snapshot.bounds)
    if element.kind == "text":
        return (text_similarity * 0.55) + (iou * 0.25) + (containment * 0.2) - (distance_penalty * 0.15)
    return (iou * 0.45) + (containment * 0.25) + (text_similarity * 0.1) + clickable_bonus - (
        distance_penalty * 0.15
    )


def _center_inside(box: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> bool:
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def _normalized_center_distance(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> float:
    acx = (a[0] + a[2]) / 2.0
    acy = (a[1] + a[3]) / 2.0
    bcx = (b[0] + b[2]) / 2.0
    bcy = (b[1] + b[3]) / 2.0
    aw = max(1.0, float(a[2] - a[0]))
    ah = max(1.0, float(a[3] - a[1]))
    bw = max(1.0, float(b[2] - b[0]))
    bh = max(1.0, float(b[3] - b[1]))
    norm = max((aw + bw) / 2.0, (ah + bh) / 2.0, 1.0)
    dx = (acx - bcx) / norm
    dy = (acy - bcy) / norm
    return (dx * dx + dy * dy) ** 0.5


def _text_similarity(a: str | None, b: str | None) -> float:
    clean_a = "".join((a or "").split()).lower()
    clean_b = "".join((b or "").split()).lower()
    if not clean_a or not clean_b:
        return 0.0
    if clean_a == clean_b:
        return 1.0
    if clean_a in clean_b or clean_b in clean_a:
        return min(len(clean_a), len(clean_b)) / max(len(clean_a), len(clean_b))
    overlap = len(set(clean_a) & set(clean_b))
    return overlap / max(len(set(clean_a) | set(clean_b)), 1)


def _enrich_element(element: ClickableElement, snapshot: TreeNodeSnapshot) -> ClickableElement:
    return replace(
        element,
        linked_tree_node_id=snapshot.node_id,
        class_name=snapshot.class_name,
        resource_id=snapshot.resource_id,
        content_desc=snapshot.content_desc,
        enabled=snapshot.enabled,
        checked=snapshot.checked,
        selected=snapshot.selected,
        clickable=snapshot.clickable,
        semantic_role=snapshot.semantic_role,
    )
