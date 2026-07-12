from cloudevents.http import CloudEvent


def main(event: CloudEvent):

    print("=" * 80)

    print("MathVerse Chapter Pipeline")

    print("=" * 80)

    print(event.data)