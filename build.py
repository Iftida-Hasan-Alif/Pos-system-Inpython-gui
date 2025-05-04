import PyInstaller.__main__

PyInstaller.__main__.run([
    'ui.py',
    '--onefile',
    '--windowed',
    '--icon=logo.png',  # You can remove this if no logo
    '--add-data=logo.png:.',  # Make sure logo.png exists
    '--add-data=pos_system.db:.',  # Ensure the DB is in the root folder
    '--hidden-import=sqlite3',
    '--hidden-import=reportlab',
    '--clean',
    '--noconfirm'
])
