# TODO List - 3270 RFC Compliance and p3270 Compatibility

## High Priority
- Add full AID support (PA keys, PF keys beyond Enter)
- Implement proper field modification tracking for RMF/RMA commands
- Implement missing s3270 actions: CircumNot(), CursorSelect(), Delete(), DeleteField(), Dup(), End(), Erase(), EraseEOF(), EraseInput(), FieldEnd(), FieldMark(), Flip(), Insert(), MoveCursor(), MoveCursor1(), NextWord(), PreviousWord(), RestoreInput(), SaveInput(), Tab(), ToggleInsert(), ToggleReverse()
- Improve macro execution to handle all s3270 command formats

## Medium Priority
- Implement advanced s3270 actions: Capabilities(), Clear(), Close(), CloseScript(), Connect(), Disconnect(), Down(), Echo(), Enter(), Execute(), Exit(), Info(), Interrupt(), Key(), KeyboardDisable(), Left(), Macro(), Newline(), Open(), PA(), PageDown(), PageUp(), PasteString(), PF(), PreviousWord(), Query(), Quit(), Right(), Script(), Set(), Up()
- Add resource definition support (xrdb format)
- Implement missing s3270 actions: AnsiText(), Bell(), Compose(), Cookie(), Expect(), Fail(), HexString(), Left2(), MonoCase(), NvtText(), Pause(), Printer(), PrintText(), Prompt(), ReadBuffer(), Reconnect(), Right2(), ScreenTrace(), Show(), Snap(), Source(), SubjectNames(), SysReq(), Toggle(), Trace(), Transfer(), Wait()
- Implement proper field attribute handling beyond basic protection/numeric

## Low Priority
- Add transparent printing support (TCPIP printer sessions)
- Implement 3270 extended attributes beyond basic field properties
- Add support for 14-bit addressing mode
- Implement light pen support and related orders
- Implement advanced field attributes (highlighting, color, etc.)
- Add IND$FILE file transfer support
- Implement structured fields and outbound 3270 DS (LU-LU sessions)
- Implement standalone s3270 command interface (stdin/stdout processing) for direct s3270 replacement

## Completed
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