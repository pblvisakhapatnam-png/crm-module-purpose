# Files saved by Word and Excel

Used by `backend/tests/test_document_upload_limits.py` as independent evidence that the upload
content checks accept what Microsoft Word and Excel actually write, and refuse each file under the
other program's extension. That module builds its other Office-format test files to the published
formats; these four were not built by the tests.

| File | Saved by | Format |
| --- | --- | --- |
| `saved-by-word-97-2003.doc` | Word | Word 97-2003 Document |
| `saved-by-excel-97-2003.xls` | Excel | Excel 97-2003 Workbook |
| `saved-by-word.docx` | Word | Word Document |
| `saved-by-excel.xlsx` | Excel | Excel Workbook |

The project owner saved them on 11 September 2026. Each holds only a line of test text, such as
"Word document 1 for testing"; none holds business data.

In these copies the author's name in the file properties is replaced by the placeholder `Tester`,
and nothing else is changed. In the `.doc` and `.xls` files the name is overwritten in place with a
placeholder of the same length, so every byte offset Office wrote is unchanged. The `.docx` and
`.xlsx` files are ZIP archives, rewritten member by member with the same parts, names and dates;
only `docProps/core.xml` differs.
