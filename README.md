# HA ARPAV River Level

Home Assistant integration for public ARPAV river-level observations.

The integration exposes hydrometric (`LIVIDRO`) measurements from ARPAV stations, together with source timestamps, data quality, provenance and ARPAV-published hydrometric threshold metadata.

## Scope

- public ARPAV river-level observations;
- source timestamps, quality and provenance;
- ARPAV-published threshold values as source metadata;
- Home Assistant configuration, polling, availability and entity lifecycle.

Current river profiles include Bacchiglione, Piave and Livenza. Profiles only select public ARPAV source stations.

## Safety

HA ARPAV River Level is informational. It is not an official civil-protection warning or emergency-alerting service.

For authoritative hydrological or hydraulic alerts, consult Regione del Veneto / Protezione Civile and official ARPAV channels.

## Compatibility

Minimum supported Home Assistant version: **2026.8.2**.

## Security

No API credential is required for the public ARPAV data source. Release gates include secret/history scanning, public-artifact hygiene checks, dependency vulnerability checks and a CycloneDX SBOM.

## Licence

Code is Apache-2.0. ARPAV source data remains subject to its own reuse and attribution terms.
