import contextlib
import io
import unittest
from unittest.mock import patch

from qfabric.cli import main


class QFabricCliTests(unittest.TestCase):
    def test_required_linux_command_shape(self) -> None:
        output = io.StringIO()
        with (
            patch("qfabric.cli.run_linux", return_value=5) as run,
            contextlib.redirect_stdout(output),
        ):
            status = main(["run", "add", "--domain", "linux", "--", "2", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "5\n")
        self.assertEqual(run.call_args.args[1:], (2, 3))

    def test_required_rt_command_shape(self) -> None:
        output = io.StringIO()
        with (
            patch("qfabric.cli.run_rt", return_value=5) as run,
            contextlib.redirect_stdout(output),
        ):
            status = main(["run", "add", "--domain", "rt", "--", "2", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "5\n")
        self.assertEqual(run.call_args.args[1:3], (2, 3))

    def test_domains_share_validation_error(self) -> None:
        errors = []
        for domain in ("linux", "rt"):
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = main(["run", "add", "--domain", domain, "--", "2"])
            self.assertEqual(status, 1)
            errors.append(error.getvalue())
        self.assertEqual(errors[0], errors[1])


if __name__ == "__main__":
    unittest.main()
