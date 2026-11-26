-- Approver authorization gate — re-notify bug fix.
-- Adds `approverGateNotifiedAmount`: the over-threshold dopłata (EUR) Approver was
-- LAST notified about via the auto-confirmation email. The api `_applyApproverGate`
-- reads it to detect when a re-verify moved the amount and Approver must be
-- re-notified. NULL when the gate was never armed/notified or was reset; nulled
-- in lockstep with the rest of the approverGate* fields.
--
-- Same precision as `paymentEur` / `amountRequested` / `origPaymentEur`
-- (DECIMAL(12,2); money is Decimal, never Float).
--
-- Physical table is `claims` (Claim model @@map). Nullable, no default →
-- backfills existing rows to NULL. Forward-only (greenfield DB per CLAUDE.md).

-- AlterTable
ALTER TABLE "claims" ADD COLUMN     "approverGateNotifiedAmount" DECIMAL(12,2);
