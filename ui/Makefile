
all: sshkbm_window.ui
	python3 -m PyQt5.uic.pyuic sshkbm_window.ui -o sshkbm_window.py
	python3 -m PyQt5.pyrcc_main bg.qrc -o bg_rc.py
	sed -i 's/^import bg_rc$$/from ui import bg_rc/' sshkbm_window.py
