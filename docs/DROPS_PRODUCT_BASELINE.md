# Drops Product Baseline

Status: Approved product direction
Date: September 4, 2026

## Purpose

Drops is for a specific retail product the user already knows they want when availability, price, variant, or pickup is the problem.

Universal Watcher should help locate the product across supported sources, normalize the offers, verify the user's criteria, and optionally keep monitoring until the criteria are met.

## V1 product identification

The user should be able to identify a product using one or more of:

- product name
- model number
- UPC / other reliable product identifier
- product URL

## V1 criteria

Drops should support criteria such as:

- in stock
- maximum price
- exact size / color / model / variant where the source exposes it
- local pickup availability where supported
- selected supported retailers or any supported retailer

## V1 product scope

Good V1 examples include:

- game consoles and electronics
- GPUs and computer hardware
- specific LEGO sets or collectibles
- limited-release merchandise
- specific appliances or hard-to-find items
- an exact size/color/model of a product
- sold-out products that the user wants Universal Watcher to keep checking

## Out of scope for V1

Drops is not a generic recommendation engine.

Do not make V1 responsible for broad questions such as "find me the best 65-inch TV" or "what laptop should I buy?" Those are shopping/recommendation problems rather than exact-item discovery and monitoring.

Do not promise every retailer on the internet. Drops should use supported, legitimate, stable data sources and expand retailer coverage only when reliable access is available.

Do not build automatic purchasing / checkout bots as part of the V1 product.

## Shared Universal Watcher pattern

Drops fits the common product model:

Discover -> Normalize -> Filter -> Verify -> Rank -> Result -> optionally Watch

The product promise is: the user already knows what they want; Universal Watcher finds where it is actually available and can keep checking until it meets the user's conditions.
