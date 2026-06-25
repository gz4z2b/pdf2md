class Pdf2MdError(Exception):
    """Base error for user-facing conversion failures."""


class PdfReadError(Pdf2MdError):
    """Raised when a PDF cannot be opened or parsed."""
