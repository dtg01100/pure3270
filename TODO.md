# TODO List - 3270 RFC Compliance and p3270 Compatibility

## Low Priority
- Add transparent printing support (TCPIP printer sessions)
- Implement 3270 extended attributes beyond basic field properties
- Add support for 14-bit addressing mode
- Implement light pen support and related orders
- Implement advanced field attributes (highlighting, color, etc.)
- Add IND$FILE file transfer support
- Implement structured fields and outbound 3270 DS (LU-LU sessions)
- Implement standalone s3270 command interface (stdin/stdout processing) for direct s3270 replacement
- Add SEQ-NUMBER correlation support
- Implement DATA-STREAM-CTL support
- Implement BIND-IMAGE passing
- Implement advanced response handling mechanisms
- Implement full LU name selection negotiation
- Implement printer status communication mechanisms
- Implement Device End/Intervention Required status handling
- Implement SOH % R S1 S2 IAC EOR status message formats

## Completed Features in v0.2.0
- Basic 3270 data stream parsing (W, SBA, SF, etc.)
- Screen buffer management with EBCDIC support
- Basic field detection and content handling
- RMF (Read Modified Fields) and RMA (Read Modified All) support
- Basic AID handling for Enter key
- p3270-compatible connect/send/read/close session interface
- String() command support with EBCDIC conversion
- key Enter command support
- Basic macro execution with command sequences
- s3270 text conversion actions: Ascii(), Ebcdic(), Ascii1(), Ebcdic1(), AsciiField(), EbcdicField()
- s3270 key actions: PF(1-24), PA(1-3), Attn(), Reset()
- s3270 cursor navigation actions: Home(), Left(), Right(), Up(), Down(), BackSpace(), Tab(), BackTab()
- TN3270E header processing with DATA-TYPE, REQUEST-FLAG, RESPONSE-FLAG, SEQ-NUMBER
- SCS-CTL-CODES support
- Printer session support with SCS character data processing
- PRINT-EOJ handling
- Resource definition support (xrdb format)
- Advanced macro execution with conditional branching and variable substitution
- s3270 actions: CircumNot(), CursorSelect(), Delete(), DeleteField(), Dup(), End(), Erase(), EraseEOF(), EraseInput(), FieldEnd(), FieldMark(), Flip(), Insert(), MoveCursor(), MoveCursor1(), NextWord(), PreviousWord(), RestoreInput(), SaveInput(), Tab(), ToggleInsert(), ToggleReverse()
- s3270 actions: Capabilities(), Clear(), Close(), CloseScript(), Connect(), Disconnect(), Down(), Echo(), Enter(), Execute(), Exit(), Info(), Interrupt(), Key(), KeyboardDisable(), Left(), Macro(), Newline(), Open(), PA(), PageDown(), PageUp(), PasteString(), PF(), PreviousWord(), Query(), Quit(), Right(), Script(), Set(), Up()
- s3270 actions: AnsiText(), Bell(), HexString(), Left2(), MonoCase(), NvtText(), Pause(), Printer(), PrintText(), Prompt(), ReadBuffer(), Reconnect(), Right2(), ScreenTrace(), Show(), Snap(), Source(), SubjectNames(), SysReq(), Toggle(), Trace(), Transfer(), Wait()
- Add full AID support (PA keys, PF keys beyond Enter)
- Implement proper field modification tracking for RMF/RMA commands
- Implement proper field attribute handling beyond basic protection/numeric
- Implement missing s3270 actions: Compose(), Cookie(), Expect(), Fail()
