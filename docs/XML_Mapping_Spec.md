# XML Mapping Specification — EUDAMED DTX schema v3.0.30

Source of truth: official EUDAMED XSD package in `xsd/` (entry point
`xsd/service/Message.xsd`). Implemented by `eudamed_tool/xml_generator.py`.

## Message envelope

Root element `m:Push` (namespace `…/servicemodel/Message/v1`), attribute
`version="3.0.30"` (fixed by the XSD). Envelope order: `correlationID`,
`creationDateTime`, `messageID`, `recipient`, `payload`, `sender`.
Recipient node actor is `EUDAMED`; sender node actor is the manufacturer SRN.
Service: `serviceID=DEVICE`, `serviceOperation=POST` (new device registration).
`serviceAccessToken` is only needed for M2M, not for bulk upload.

The payload carries 1..300 `device:Device` elements with
`xsi:type="device:MDRDeviceType"`, each containing one `device:MDRBasicUDI`
and one `device:MDRUDIDIData`.

## Namespace prefixes

| Prefix | Namespace (…= `https://ec.europa.eu/tools/eudamed/dtx`) |
|---|---|
| m | …/servicemodel/Message/v1 |
| s | …/servicemodel/Service/v1 |
| device | …/datamodel/Entity/Device/v1 |
| basicudi | …/datamodel/Entity/Device/BasicUDI/v1 |
| udidi | …/datamodel/Entity/UDIDI/v1 |
| commondi | …/datamodel/Entity/Device/CommonDevice/v1 |
| marketinfo | …/datamodel/Entity/MktInfo/MarketInfo/v1 |
| lsn | …/datamodel/Entity/Common/LanguageSpecific/v1 |

## MDRBasicUDI mapping (element order is normative)

| Source field | XML element | Req | Notes |
|---|---|---|---|
| risk_class | basicudi:riskClass | Yes | MDR subset: CLASS_I / CLASS_IIA / CLASS_IIB / CLASS_III |
| model_name | basicudi:modelName / commondi:name | Yes | model (commondi:model) optional, not currently used |
| basic_udi_di + issuing_entity_code | basicudi:identifier / commondi:DICode + issuingEntityCode | Yes | DICode max 120 chars |
| animal_tissues_cells | basicudi:animalTissuesCells | Yes | |
| human_tissues_cells | basicudi:humanTissuesCells | Yes | |
| manufacturer_srn | basicudi:MFActorCode | Yes | SRN pattern CC-MF-######### |
| human_product_check | basicudi:humanProductCheck | Yes | |
| medicinal_product_check | basicudi:medicinalProductCheck | Yes | |
| device_type | basicudi:type | Yes | DEVICE / SYSTEM / PROCEDURE_PACK |
| active … reusable | commondi:active, administeringMedicine, implantable, measuringFunction, reusable | Yes | MDApplicablePropertiesGroup, this exact order |

Not yet mapped (optional in XSD, add when needed): ARActorCode (authorised
representative — required for non-EU manufacturers), specialDevice,
IIb_implantable_exceptions, certificate links.

## MDRUDIDIData mapping (element order is normative)

| Source field | XML element | Req | Notes |
|---|---|---|---|
| udi_di + issuing_entity_code | udidi:identifier / commondi:DICode + issuingEntityCode | Yes | |
| device_status | udidi:status / commondi:code | Yes | ON_THE_MARKET etc. |
| basic_udi_di | udidi:basicUDIIdentifier / commondi:DICode + issuingEntityCode | Yes | reference to the Basic UDI-DI |
| emdn_codes[] | udidi:MDNCodes | Yes | ONE element, space-separated EMDN codes (xs:list) |
| production_identifiers[] | udidi:productionIdentifier | Cond | ONE element, space-separated PIElementEnum values |
| reference_number | udidi:referenceNumber | Yes | max 255 chars |
| — | udidi:secondaryIdentifier | No | not mapped |
| sterile | udidi:sterile | Yes | |
| sterilization | udidi:sterilization | Yes | |
| trade_names[] | udidi:tradeNames / lsn:name (lsn:language + lsn:textValue) | No | language from lsn:LanguageEnum (EN, DE, ANY, …) |
| number_of_reuses | udidi:numberOfReuses | Yes | -1 = not applicable, 0 = single use, >0 = limited reuses |
| market_countries[] | udidi:marketInfos / marketinfo:marketInfo | No | order: country, endDate?, originalPlacedOnTheMarket, startDate?; originalPlacedOnTheMarket is derived: TRUE for DE, FALSE for all other countries (not a workbook column) |
| direct_marking_di | udidi:deviceMarking / udidi:directMarkingDI | No | |
| base_quantity | udidi:baseQuantity | Yes* | required for Regulation devices |
| latex | udidi:latex | Yes | |
| reprocessed | udidi:reprocessed | Yes | |

Not yet mapped (optional): additionalDescription, website,
storageHandlingConditions, packages (container packaging), criticalWarnings,
substances (CMR/endocrine/medicinal), clinicalSizes, annexXVI fields,
unitOfUseIdentifier, productDesignerActor.

## Key vocabulary corrections vs. the earlier draft spec

- Production identifiers: `BATCH_NUMBER` (not LOT_NUMBER), `SOFTWARE_IDENTIFICATION` (not SOFTWARE_VERSION)
- Risk classes: no CLASS_IR/IM/IS — Class I variants are CLASS_I + applicable property flags
- Device type: three values (DEVICE / SYSTEM / PROCEDURE_PACK)
- Issuing entities include EUDAMED
- Market countries restricted to EU/EEA enum (Greece = EL, Northern Ireland = XI)
- Trade-name languages from lsn:LanguageEnum (upper-case ISO codes + ANY)
