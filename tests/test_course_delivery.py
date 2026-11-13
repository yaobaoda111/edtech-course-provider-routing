import pytest

from src.course_delivery import CourseDelivery, routing_choice


def test_routing_choice_excludes_incumbent_for_a_reportable_course():
    delivery = CourseDelivery("math-101", "learner-7", "2026-11-15", True)

    assert routing_choice(delivery, "incumbent-provider") == {
        "capability": "account.routing.set",
        "exclude": "incumbent-provider",
    }


def test_routing_choice_requires_the_educator_report():
    delivery = CourseDelivery("math-101", "learner-7", "2026-11-15", False)

    with pytest.raises(ValueError, match="educator reporting"):
        routing_choice(delivery, "incumbent-provider")
