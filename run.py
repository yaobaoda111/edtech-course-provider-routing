import os

from src.course_delivery import CourseDelivery, InfraiClient, migrate_course_delivery


def main() -> None:
    delivery = CourseDelivery("math-101", "learner-7", "2026-11-15", True)
    result = migrate_course_delivery(InfraiClient(os.environ.get("INFRAI_API_KEY")), delivery, "incumbent-provider")
    print(result)


if __name__ == "__main__":
    main()
