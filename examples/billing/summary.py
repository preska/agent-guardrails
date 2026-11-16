"""A friendly one-line summary for the invoice email."""

from anthropic import Anthropic

from examples.billing.invoice import Invoice

client = Anthropic()


def summarize(invoice: Invoice) -> str:
    reply = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=60,
        messages=[{"role": "user", "content": f"One friendly line about invoice {invoice.number}."}],
    )
    return reply.content[0].text
