# Set Style Sheets:
# toolTip
tool_tip = 'QToolTip { background-color: grey; color: white; border: black 0px}'

# button
color_button_disabled       = '* { color: rgb(100,100,100); background-color: rgb(75,75,75)} %s'%(tool_tip)
color_button_enabled        = '* { color: rgb(250,250,250); background-color: rgb(40,40,40)} %s'%(tool_tip)
#color_button_enabled        = '* { color: rgb(250,250,250); background-color: rgb(100,150,250)} %s'%(tool_tip)
color_button_secondary      = '* { color: rgb(250,250,250); background-color: rgb(150,150,150)} %s'%(tool_tip)
color_button_warning        = '* { color: rgb(250,250,250); background-color: rgb(250,150,100)} %s'%(tool_tip)

# checkBox
color_checkbox_disabled     = '* { color: rgb(100,100,100)} %s'%(tool_tip)
color_checkbox_enabled      = '* { color: rgb(200,200,200)} %s'%(tool_tip)

# lineEdit
color_lineEdit_locked       = '* { color: rgb(200,200,200); background-color: rgb(100,100,100)} %s'%(tool_tip)
color_lineEdit_enabled      = '* { color: rgb(200,200,200); background-color: rgb(40,40,40)} %s'%(tool_tip)
color_lineEdit_warning      = '* { color: rgb(250,250,250); background-color: rgb(250,150,100)} %s'%(tool_tip)

# label
color_label_medium          = '* { color: rgb(200,200,200)} %s'%(tool_tip)
color_label_small           = '* { color: rgb(200,200,200)} %s'%(tool_tip)

# seperator
color_seperator             = '* { color: rgb(250,250,250); background-color: rgb(40,40,40)} %s'%(tool_tip)

# tab
color_tab_medium            = '* { color: rgb(250,250,250) } QTabWidget::tab-bar { border: 0px } %s'%(tool_tip)
color_tab_small             = '* { color: rgb(250,250,250) } QTabWidget::tab-bar { border: 0px } %s'%(tool_tip)

# listWidget
#list_focus_policy           = '* { color: rgb(250,250,250) } QListWidget::setFocusPolicy { border: 0px } %s'%(tool_tip)
#frame_selection_bg_color    = '*
#list_selection              = '* { color: rgb(250,250,250) } QListWidget::setFocusPolicy { border: 0px } %s'%(tool_tip)

# status
color_status_default        = '* { color: rgb(200,200,200); border: 0px} %s'%(tool_tip)
color_status_clear          = '* { color: rgb(200,200,200); background-color: rgb(40,40,40); border: 0px} %s'%(tool_tip)
color_status_warning        = '* { color: rgb(100,100,100); background-color: rgb(235,240,130); border: 0px} %s'%(tool_tip)
color_status_success        = '* { color: rgb(250,250,250); background-color: rgb(55,200,130); border: 0px} %s'%(tool_tip)
color_status_working        = '* { color: rgb(250,250,250); background-color: rgb(100,150,250); border: 0px} %s'%(tool_tip)
color_status_error          = '* { color: rgb(250,250,250); background-color: rgb(225,115,100); border: 0px} %s'%(tool_tip)

"""
# Set Style Sheets:
# toolTip
tool_tip = 'QToolTip { font-size: 10px; background-color: grey; color: white; border: black 0px}'

# button
color_button_disabled       = '* { font-size: 12px; color: rgb(100,100,100); background-color: rgb(75,75,75)} %s'%(tool_tip)
color_button_enabled        = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(100,150,250)} %s'%(tool_tip)
color_button_secondary      = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(150,150,150)} %s'%(tool_tip)
color_button_warning        = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(250,150,100)} %s'%(tool_tip)

# checkBox
color_checkbox_disabled     = '* { font-size: 12px; color: rgb(100,100,100)} %s'%(tool_tip)
color_checkbox_enabled      = '* { font-size: 12px; color: rgb(200,200,200)} %s'%(tool_tip)

# lineEdit
color_lineEdit_locked       = '* { font-size: 12px; color: rgb(200,200,200); background-color: rgb(100,100,100)} %s'%(tool_tip)
color_lineEdit_enabled      = '* { font-size: 12px; color: rgb(200,200,200); background-color: rgb(40,40,40)} %s'%(tool_tip)
color_lineEdit_warning      = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(250,150,100)} %s'%(tool_tip)

# label
color_label_medium          = '* { font-size: 14px; color: rgb(200,200,200)} %s'%(tool_tip)
color_label_small           = '* { font-size: 12px; color: rgb(200,200,200)} %s'%(tool_tip)

# seperator
color_seperator             = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(40,40,40)} %s'%(tool_tip)

# tab
color_tab_medium            = '* { font-size: 14px; color: rgb(250,250,250) } QTabWidget::tab-bar { border: 0px } %s'%(tool_tip)
color_tab_small             = '* { font-size: 12px; color: rgb(250,250,250) } QTabWidget::tab-bar { border: 0px } %s'%(tool_tip)

# status
color_status_default        = '* { font-size: 12px; color: rgb(200,200,200); border: 0px} %s'%(tool_tip)
color_status_clear          = '* { font-size: 12px; color: rgb(200,200,200); background-color: rgb(40,40,40); border: 0px} %s'%(tool_tip)
color_status_warning        = '* { font-size: 12px; color: rgb(100,100,100); background-color: rgb(235,240,130); border: 0px} %s'%(tool_tip)
color_status_success        = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(55,200,130); border: 0px} %s'%(tool_tip)
color_status_working        = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(100,150,250); border: 0px} %s'%(tool_tip)
color_status_error          = '* { font-size: 12px; color: rgb(250,250,250); background-color: rgb(225,115,100); border: 0px} %s'%(tool_tip)

"""
