import sys

from django.core.management.commands.test import Command as TestCommand

from south.management.commands import patch_for_test_db_setup



class Command(TestCommand):
    help = (
        "Runs the test modules, cases, or methods specified "
        "by dotted path on the command line, or does test "
        "discovery if no arguments are given."
        )
    args = "[dotted-path ...]"

    requires_model_validation = False

    def handle(self, *test_labels, **options):
        patch_for_test_db_setup()

        from django.conf import settings
        from django.test.utils import get_runner

        verbosity = int(options.get('verbosity', 1))
        interactive = options.get('interactive', True)
        failfast = options.get('failfast', False)
        TestRunner = get_runner(settings)

        test_runner = TestRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
        failures = test_runner.run_tests(test_labels)

        sys.exit(bool(failures))
