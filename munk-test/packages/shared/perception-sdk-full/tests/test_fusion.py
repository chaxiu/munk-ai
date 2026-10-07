from munk.perception.types import IconDetection, TextDetection
from munk_perception_full.fusion import fuse_elements


def test_fuse_elements_preserves_word_separators_as_single_spaces() -> None:
    elements = fuse_elements(
        icons=[IconDetection(box=(0, 0, 200, 80), score=0.9)],
        texts=[
            TextDetection(
                box=(10, 10, 190, 40),
                text="  Doctor   appointment   [High]  ",
                score=0.98,
            )
        ],
    )

    assert [element.text for element in elements] == [
        "Doctor appointment [High]",
        "Doctor appointment [High]",
    ]
