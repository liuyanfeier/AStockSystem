"""Safe, stable failures shared by slice admission and offline verification."""


class SliceStop(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ReceiptIntegrityError(SliceStop):
    def __init__(self, code: str, *, expected: int | None = None,
                 observed: int | None = None):
        self.expected = expected
        self.observed = observed
        super().__init__(code)

    def summary(self) -> dict:
        return dict(verdict='BLOCKED', reason_code=self.code,
                    expected=self.expected, observed=self.observed)
