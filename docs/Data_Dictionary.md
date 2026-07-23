# Data Dictionary - EUDAMED MDR UDI/Device Registration

## Basic UDI-DI
| Field | Type | Mandatory | XML Path | Description |
|---|---|---|---|---|
| basic_udi_di | varchar(100) | Yes | MDRBasicUDI/identifier/DICode | Basic UDI-DI assigned to the device family. |
| issuing_entity_code | enum | Yes | MDRBasicUDI/identifier/issuingEntityCode | UDI issuing entity. |
| manufacturer_srn | varchar(50) | Yes | MDRBasicUDI/MFActorCode | Manufacturer actor / SRN code. |
| risk_class | enum | Yes | MDRBasicUDI/riskClass | MDR risk class. |
| model_name | varchar(250) | Yes | MDRBasicUDI/modelName | Model or device family name. |
| device_type | enum | Yes | MDRBasicUDI/type | Device or system/procedure pack. |
| animal_tissues_cells | boolean | Yes | MDRBasicUDI/animalTissuesCells | Animal tissue/cell flag. |
| human_tissues_cells | boolean | Yes | MDRBasicUDI/humanTissuesCells | Human tissue/cell flag. |
| human_product_check | boolean | Yes | MDRBasicUDI/humanProductCheck | Human product derivative flag. |
| medicinal_product_check | boolean | Yes | MDRBasicUDI/medicinalProductCheck | Medicinal substance flag. |
| administering_medicine | boolean | Yes | MDRBasicUDI/administeringMedicine | Administers medicine flag. |
| active | boolean | Yes | MDRBasicUDI/active | Active device flag. |
| implantable | boolean | Yes | MDRBasicUDI/implantable | Implantable device flag. |
| measuring_function | boolean | Yes | MDRBasicUDI/measuringFunction | Measuring function flag. |
| reusable | boolean | Yes | MDRBasicUDI/reusable | Reusable device flag. |

## Device / UDI-DI
| Field | Type | Mandatory | XML Path | Description |
|---|---|---|---|---|
| udi_di | varchar(100) | Yes | MDRUDIDIData/identifier/DICode | UDI-DI of individual device. |
| issuing_entity_code | enum | Yes | MDRUDIDIData/identifier/issuingEntityCode | UDI issuing entity. |
| basic_udi_di_id | uuid/fk | Yes | MDRUDIDIData/basicUDIIdentifier/DICode | Link to Basic UDI-DI. |
| reference_number | varchar(100) | Yes | MDRUDIDIData/referenceNumber | Internal or commercial reference number. |
| device_status | enum | Yes | MDRUDIDIData/status/code | Market status. |
| sterile | boolean | Yes | MDRUDIDIData/sterile | Supplied sterile flag. |
| sterilization | boolean | Yes | MDRUDIDIData/sterilization | Sterilization required flag. |
| number_of_reuses | integer | Yes | MDRUDIDIData/numberOfReuses | Number of permitted reuses. |
| base_quantity | integer | Yes | MDRUDIDIData/baseQuantity | Base quantity. |
| latex | boolean | Yes | MDRUDIDIData/latex | Contains latex flag. |
| reprocessed | boolean | Yes | MDRUDIDIData/reprocessed | Reprocessed device flag. |
