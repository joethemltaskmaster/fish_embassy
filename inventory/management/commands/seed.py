from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load sample data (Supplier A, Customer 1, frozen chicken 20 kg)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "Seed command exists but no models yet — Stage 3 adds real data."
        ))