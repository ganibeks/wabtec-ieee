# GE IGBT assembly identification — web research, 2026-10-17

Conclusion: related GE positive/negative inverter assembly families; the two user URLs do not establish identical or interchangeable hardware. No model parameters were changed.

## Direct supplier records

- User Elixir URL: https://www.elixirengineering.com/products/igbt lists IGBT+, GE1255, with other OEM numbers 17FM796A1 /A2/A3. This is a supplier cross-reference, not an OEM interchangeability approval.
- A separate Elixir page is an exact part-number match to the IndiaMART URL: https://www.elixirengineering.com/products/complete-igbt-module-ve lists Complete IGBT Module +Ve, 17FM774A1.
- The paired negative complete assembly is 17FM775A1: https://www.elixirengineering.com/products/complete-igbt-module-ve-2 . Positive/negative assembly labels do not mean P-channel/N-channel semiconductor types.
- https://woodrichglobal.in/igbt/ explicitly separates GE locomotive 17FM774A1/17FM775A1 from mining truck 17FM796A1/A2/A3 GE1255 and 17FM797A1/A2/A3 GE1256. Supplier application labels do not prove universal exclusivity or interchangeability.
- The IndiaMART page could not be retrieved. Only its URL identifies 17FM774A1; its seller, electrical specifications, photographs and revision were not independently verified.
- Elixir's Technical Datasheet link on the original product leads to a contact page, not an openly downloadable device datasheet.

## Internal semiconductor lead — not a confirmed identification

https://www.controland.com/17fm796-17fm797/ describes complete aftermarket assemblies, driver/module repair kits, and a green-sticker assembly associated with Hitachi MBN1200E25C. It covers many GE part numbers, so this must not be generalized into a confirmed semiconductor BOM for every 17FM774/796 revision.

A Hitachi-authored MBN1200E25C datasheet copy, specification IGBT-SP-05023 R2, is publicly mirrored at:
https://gazellec.com/wp-content/uploads/2018/07/MBN1200E25C-Hitachi-IGBT-Module_DataSheet.pdf
It specifies 2500 V VCES, 1200 A DC collector current under its stated conditions, and +/-20 V absolute gate rating. These values apply to that exact semiconductor, not automatically to an assembled panel. A manufacturer-origin document hosted on a third-party site is not confirmation of authenticity, current revision or compatibility with the target Wabtec assembly.

## Implication for the electrical test cell

Treat the complete phase assembly and the internal semiconductor as different identification levels. An assembly can include its driver and power interconnects, so semiconductor C/E/G characterization alone does not establish complete assembly functionality. Exact driver supply, command/feedback interface, polarity, pinout and protection behavior need assembly documentation.

The existing CM1500HC-66XB traction parameter set remains a representative surrogate. Neither the two user links nor the research establishes it as the semiconductor in 17FM774A1. Do not silently replace it with MBN1200E25C either.

To close identification: obtain the assembly nameplate and revision, semiconductor marking, driver board part number, assembly connection drawing and OEM compatibility record. Until then, part family identification is useful; exact electrical ratings, test conditions and acceptance limits remain unresolved.
