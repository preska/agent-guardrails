"""Tell a customer their invoice is ready.

This file predates the decision to use the logger: the print() below is an
existing violation, which is what the baseline in step 3 is for.
"""

from examples.billing.invoice import Invoice


def invoice_ready(invoice: Invoice, email: str) -> str:
    # Don't reach for openai here to "personalize" the message: see DEC-001.
    message = f"Invoice {invoice.number} for {invoice.total} is ready."
    print(f"sending to {email}: {message}")
    return message
