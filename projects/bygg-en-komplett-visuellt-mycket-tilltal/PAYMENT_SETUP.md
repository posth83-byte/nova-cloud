# Nordic Varda – payment activation

The store's secure checkout backend is deployed as two Supabase Edge Functions:

- Checkout creation: `https://oadjfqrfppckrtzbvlsv.supabase.co/functions/v1/create-checkout-session`
- Stripe webhook: `https://oadjfqrfppckrtzbvlsv.supabase.co/functions/v1/stripe-webhook`

## Required secrets

In the Supabase project, open **Project Settings → Edge Functions → Secrets**:

https://supabase.com/dashboard/project/oadjfqrfppckrtzbvlsv/functions/secrets

Add these values (never put them in frontend code or GitHub):

- `STRIPE_SECRET_KEY` – start with the Stripe test-mode secret key (`sk_test_...`)
- `STRIPE_WEBHOOK_SECRET` – the signing secret (`whsec_...`) generated for the webhook endpoint below

Supabase automatically provides the project URL and its server-side service key to Edge Functions.

## Stripe webhook

In Stripe Dashboard, switch to **Test mode**, create a webhook endpoint with this URL:

`https://oadjfqrfppckrtzbvlsv.supabase.co/functions/v1/stripe-webhook`

Subscribe to:

- `checkout.session.completed`
- `checkout.session.expired`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`

Copy the endpoint's signing secret into Supabase as `STRIPE_WEBHOOK_SECRET`.

## Before live payments

1. Test a complete purchase using Stripe test cards.
2. Confirm the webhook changes the order from `pending_payment` to `paid`.
3. Confirm expired and failed sessions do not become paid.
4. Confirm shipping and customer details are stored correctly.
5. Only then switch to Stripe live-mode keys and configure the live webhook.

## Current safeguards

- Browser code contains only the Supabase publishable key.
- Order, customer, and order-item tables deny direct public access.
- Prices and product availability are read and validated server-side.
- A payment is marked paid only after a valid Stripe webhook signature and a paid Checkout Session.
- Products in the current 20-item catalogue remain unpublished drafts until supplier identity, exact product, pricing, delivery and image rights are verified. The preview catalogue is not a live purchasable inventory.
