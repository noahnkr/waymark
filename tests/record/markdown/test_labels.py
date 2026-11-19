"""The labels module: one place that writes label lines and reads them in any form."""

from waymark.record.markdown.labels import LabelForm, label_line, read_label


def test_label_line_writes_the_bold_form() -> None:
    assert label_line("Owner", "Ada") == "- **Owner:** Ada"
    assert label_line("Criteria") == "- **Criteria:**"
    assert label_line("Decided by", "human", bullet=False) == "**Decided by:** human"


def test_bold_form_with_the_colon_inside() -> None:
    label = read_label("- **Owner:** Ada")
    assert label is not None
    assert (label.name, label.value, label.form, label.bullet) == (
        "Owner",
        "Ada",
        LabelForm.BOLD,
        True,
    )


def test_plain_form() -> None:
    label = read_label("Decided by: planner ")
    assert label is not None
    assert (label.name, label.value, label.form, label.bullet) == (
        "Decided by",
        "planner",
        LabelForm.PLAIN,
        False,
    )


def test_bold_form_with_the_colon_outside() -> None:
    label = read_label("* **User-visible**: a new flag")
    assert label is not None
    assert (label.name, label.value, label.form) == (
        "User-visible",
        "a new flag",
        LabelForm.COLON_OUTSIDE,
    )


def test_a_label_without_a_value() -> None:
    for text in ("- **Criteria:**", "- Criteria:", "- **Criteria**:"):
        label = read_label(text)
        assert label is not None
        assert (label.name, label.value) == ("Criteria", "")


def test_other_lines_are_not_labels() -> None:
    for text in (
        "- the help text names the limit",
        "- **bold** prose: with a colon",
        "Criteria",
        "- (accepted) 2026-11-18 fingerprint 0123456789abcdef items 1.1 by Ada",
    ):
        assert read_label(text) is None
