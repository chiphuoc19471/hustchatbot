import os
import sys
import subprocess
import time
import webbrowser
import socket

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    print(" ĐANG KHỞI CHẠY HỆ THỐNG CHATBOT")
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(workspace_dir, "backend")
    frontend_path = os.path.join(workspace_dir, "frontend", "index.html")
    
    # Path to virtual environment python executable
    venv_python = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        # Fallback to system python if venv isn't found (though we created it)
        print(" Không tìm thấy môi trường ảo venv. Sử dụng Python hệ thống...")
        venv_python = sys.executable

    backend_process = None
    
    # 1. Start Backend FastAPI server if port 8001 is free
    if is_port_in_use(8001):
        print("ℹCổng 8001 đã được sử dụng. Có thể server Backend đã chạy sẵn từ trước.")
    else:
        print(" Đang khởi chạy Backend FastAPI...")
        try:
            backend_process = subprocess.Popen(
                [venv_python, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
                cwd=backend_dir
            )
        except Exception as e:
            print(f" Lỗi khởi chạy Backend: {e}")
            return
            
        print(" Đang chờ server Backend khởi động...")
        for _ in range(10):
            time.sleep(0.5)
            if is_port_in_use(8001):
                print(" Backend đã khởi động thành công tại http://127.0.0.1:8001")
                break
        else:
            print(" Server khởi động lâu hơn dự kiến. Tiếp tục mở Frontend...")

    # 2. Open Frontend in browser
    if os.path.exists(frontend_path):
        print(" Đang mở giao diện Chatbot trên trình duyệt...")
        frontend_url = "file://" + os.path.abspath(frontend_path).replace("\\", "/")
        webbrowser.open(frontend_url)
    else:
        print(f" Không tìm thấy file Frontend tại: {frontend_path}")

    # Keep script alive to hold the backend subprocess and print its logs
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang tắt server...")
        if backend_process:
            backend_process.terminate()
            backend_process.wait()
        print("Đã dừng toàn bộ hệ thống. See you later!")

if __name__ == "__main__":
    main()
