"""
TC-4: 文档上传（P2）

验证：上传文件 → doc tag 出现
"""
import os


def test_file_upload_shows_tag(page, base_url, take_screenshot):
    """上传文档后显示文档标签"""
    page.goto(base_url, wait_until="networkidle")

    # 创建临时测试文件
    test_file = "/tmp/e2e_test_doc.md"
    with open(test_file, "w") as f:
        f.write("# Test Document\n\nThis is test content for E2E.")

    try:
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(test_file)

        # 等待 doc tag 出现
        doc_tag = page.locator(".code-doc-tag")
        doc_tag.first.wait_for(state="visible", timeout=10000)
        take_screenshot("file_uploaded")
        assert doc_tag.count() >= 1
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
