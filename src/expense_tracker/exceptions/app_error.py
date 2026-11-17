from expense_tracker.exceptions.error_codes import AppErrorCode


class AppError(Exception):
    def __init__(self, error_code: AppErrorCode) -> None:
        super().__init__(error_code.value.code)
        self.error = error_code
