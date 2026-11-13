"""CSV export for the finance team.

Written before DEC-002. The float() below is an existing violation: it is
recorded in the baseline so adopting the rule doesn't mean fixing it first.
"""

import csv
import io

from examples.billing.invoice import Invoice


def to_csv(invoices: list[Invoice]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["number", "region", "total"])
    for invoice in invoices:
        writer.writerow([invoice.number, invoice.region, float(invoice.total)])
    return out.getvalue()
