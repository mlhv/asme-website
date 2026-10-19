from asmesite.ids import drive_id

ID = "1AbC_dEf-123456789"

def test_file_url():        assert drive_id(f"https://drive.google.com/file/d/{ID}/view?usp=sharing") == ID
def test_open_id_url():     assert drive_id(f"https://drive.google.com/open?id={ID}") == ID
def test_folder_url():      assert drive_id(f"https://drive.google.com/drive/folders/{ID}?usp=drive_link") == ID
def test_sheet_url():       assert drive_id(f"https://docs.google.com/spreadsheets/d/{ID}/edit#gid=0") == ID
def test_bare_id():         assert drive_id(f"  {ID} ") == ID
def test_blank_and_none():  assert drive_id("") is None and drive_id(None) is None
def test_non_google_text(): assert drive_id("see instagram") is None
