# Test Customer Personas

Each test customer represents a specific onboarding scenario.

| ID    | Name            | Stage              | Scenario                                       |
|-------|-----------------|--------------------|-------------------------------------------------|
| TC001 | Priya Sharma    | EKYC_PENDING       | Fresh approval, first contact, happy path       |
| TC002 | Rahul Mehta     | EKYC_PENDING       | Hindi speaker, one prior no-answer call         |
| TC003 | Ananya Iyer     | VKYC_PENDING       | eKYC done, first VKYC attempt, no prior calls   |
| TC004 | Vikram Patel    | VKYC_PENDING       | Failed VKYC once (timeout), two prior calls     |
| TC005 | Deepika Nair    | ACTIVATION_PENDING | All KYC done, high limit, first activation call |
| TC006 | Arjun Reddy     | ACTIVATION_PENDING | Low limit, not eligible for revision, 2 calls   |
| TC007 | Kavya Krishnan  | CARD_ACTIVE        | Fully activated, orientation call pending        |
| TC008 | Ravi Kumar      | EKYC_PENDING       | Consent NOT given (call should be blocked)       |
| TC009 | Sneha Gupta     | EKYC_PENDING       | Referral customer, high limit, happy path        |
| TC010 | Aditya Joshi    | VKYC_PENDING       | Premium customer (500K limit), first VKYC        |

## Edge Case Customers

- **TC008** (Ravi Kumar): `consent_status: false`. The orchestrator should refuse to call this customer and fall back to SMS-only.
- **TC004** (Vikram Patel): Previous VKYC failure + `limit_revision_eligible: false`. Tests both the retry flow and the low-limit objection without a revision lever.
- **TC006** (Arjun Reddy): High risk tier, 2 prior calls with deferrals. Tests urgency escalation logic.
