"""
Generate test Excel file with Vietnamese content
to verify Unicode support in Docling converter
"""

import openpyxl
from pathlib import Path

def create_vietnamese_test_excel():
    """Create Excel with Vietnamese content"""
    wb = openpyxl.Workbook()
    
    # Sheet 1: Vietnamese
    ws1 = wb.active
    ws1.title = "Tiếng Việt"
    
    ws1['A1'] = 'Họ và tên'
    ws1['B1'] = 'Tuổi'
    ws1['C1'] = 'Thành phố'
    ws1['D1'] = 'Nghề nghiệp'
    
    ws1['A2'] = 'Nguyễn Văn An'
    ws1['B2'] = 25
    ws1['C2'] = 'Hà Nội'
    ws1['D2'] = 'Kỹ sư phần mềm'
    
    ws1['A3'] = 'Trần Thị Bình'
    ws1['B3'] = 30
    ws1['C3'] = 'Hồ Chí Minh'
    ws1['D3'] = 'Giáo viên'
    
    ws1['A4'] = 'Lê Văn Cường'
    ws1['B4'] = 28
    ws1['C4'] = 'Đà Nẵng'
    ws1['D4'] = 'Bác sĩ'
    
    # Add some summary text with many accents
    ws1['A6'] = 'Mô tả:'
    ws1['A7'] = 'Đây là tệp kiểm tra tiếng Việt với đầy đủ các dấu câu.'
    ws1['A8'] = 'A Ă Â E Ê I O Ô Ơ U Ư Y Đ a ă â e ê i o ô ơ u ư y đ'
    ws1['A9'] = 'Sắc Huyền Hỏi Ngã Nặng: á à ả ã ạ'
    
    # Sheet 2: Mixed Vietnamese and English
    ws2 = wb.create_sheet("Song ngữ")
    
    ws2['A1'] = 'Vietnamese'
    ws2['B1'] = 'English'
    
    ws2['A2'] = 'Xin chào thế giới'
    ws2['B2'] = 'Hello World'
    
    ws2['A3'] = 'Cộng hòa Xã hội Chủ nghĩa Việt Nam'
    ws2['B3'] = 'Socialist Republic of Vietnam'
    
    ws2['A4'] = 'Độc lập - Tự do - Hạnh phúc'
    ws2['B4'] = 'Independence - Freedom - Happiness'
    
    # Save
    output_dir = Path(__file__).parent / 'input'
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / 'vietnamese_test.xlsx'
    wb.save(output_path)
    print(f"Created Vietnamese test Excel: {output_path}")
    print(f"Sheets: {[ws.title for ws in wb.worksheets]}")
    
    return output_path

if __name__ == '__main__':
    create_vietnamese_test_excel()
