import pd
import npyscreen
import time
import multiprocessing as mp
import logging
import ansiblelib
import signal
import os
import sys
import pyperclip



def handler(signum, frame):
    if os.path.exists(os.getcwd() + '/env/passwords'):
        os.remove(os.getcwd() + '/env/passwords')
        sys.exit("bye-bye, passfile was deleted")
    else:
        sys.exit("bye-bye")
    return


def ack_the_alerts():
    while True:
        state = bool(pd.get_alerts('forack'))
        time.sleep(3)
        if state:
            pd.ack()
    return


class Ackbutton(npyscreen.TitleSelectOne):
    def when_value_edited(self):
        if self.value == [0]:
            global pool
            pool = mp.Pool(1)
            pool.apply_async(ack_the_alerts)
        elif self.value == [1]:
            if 'pool' in locals():
                pool.terminate()
            return



class Button(npyscreen.ButtonPress):
    pass


class MessageForm(npyscreen.MultiLineEdit):
    pass


class Preview_Window(npyscreen.BoxTitle):
    _contained_widget = MessageForm


class PDinfo(npyscreen.SelectOne):
    pass


class MainScreen(npyscreen.NPSAppManaged):
    selected_chatlist, selected_userlist, pasteflag, the_alert = None, None, None, None

    def onStart(self):
        self.mainform = self.addForm("MAIN", NOCTool, name='NOCTool')
        self.chatmenu = self.addForm("CHAT", ChatMenu)
        self.usermenu = self.addForm("USER", UserMenu)
        self.actionmenu = self.addForm("ACTION", ActionMenu)
        self.confirm = self.addForm("CONFIRM", Confirmation, name='Are you shure?')


class ActionMenu(npyscreen.FormBaseNew):
    def create(self):
        self.display()
        self.host = self.add(Preview_Window, name='Selected Host',
                             max_height=4, width=40, editable=False)
        self.user = self.add(Preview_Window, name='Set Login User', max_height=4,
                             width=40, value_changed_callback=self.hide_user_set)
        self.passfield = self.add(npyscreen.TitlePassword, name="Set sudo pass",
                                  value_changed_callback=self.hide_user_set)
        self.create_pass_f = self.add(Button, name='Set user/pass data',
                                      when_pressed_function=self.gen_f)
        # self.beanstalk = self.add(Button,
        #                       name="Grep beanstalk logs")
        self.connkey = self.add(npyscreen.TitleFixedText, name='Key connected', hidden=True)
        self.conn_user_pass = self.add(npyscreen.TitleFixedText, name='User data is set', hidden=True)
        self.paste = self.add(npyscreen.TitleSelectOne, name="Hide Output in a file",
                              max_height=4,
                              value_changed_callback=self.return_paste,
                              values=['Yes', 'No'],
                              scroll_exit=True)
        self.puppet_log = self.add(Button, name='puppet_log', when_pressed_function=self.do_pupet_log)
        self.back = self.add(Button, name="Back to maintab",
                             when_pressed_function=self.switch_to_main)

        self.stdout = self.add(Preview_Window, name='Raw stdout')

    def do_pupet_log(self):
        ansiblelib.run_grep_puppet()
        with open('ansout.txt', 'r+') as f:
            self.stdout.entry_widget.value = f.read()
        f.close()
        self.display()
        return

    def gen_f(self):
        if self.user.entry_widget.value and self.passfield.value:
            ansiblelib.gen_files(self.passfield.value, self.user.value)
            self.conn_user_pass.hidden = False
            self.display()
        else:
            npyscreen.notify_confirm('User or pass is not Set', title='Error')

    def create_symlink(self):
        if self.select_key.value:
            create = ansiblelib.create_symlink(self.select_key.value)
            logging.debug(create)
            self.connkey.hidden = False
            self.display()
        else:
            npyscreen.notify_confirm('Key is not set', title='Error')

    def hide_user_set(self, widget):
        self.conn_user_pass.hidden = True
        self.display()

    def return_paste(self, widget):
        if self.paste.value == [0]:
            self.parentApp.pasteflag = True
            print(self.parentApp.pasteflag)
        else:
            self.parentApp.pasteflag = False

    def on_ok(self):
        self.parentApp.switchForm("MAIN")

    def on_cancel(self):
        self.parentApp.switchForm("MAIN")

    def switch_to_main(self):
        self.parentApp.switchForm("MAIN")


class ChatMenu(npyscreen.ActionPopup):
    def create(self):
        self.chatlist = self.add(npyscreen.TitleMultiSelect,
                                 name="Chat select",
                                 values=pd.get_chat('chat', 'list'),
                                 scroll_exit=True)

    def on_ok(self):
        chatlist = self.chatlist.get_selected_objects()
        self.parentApp.selected_chatlist = chatlist

        self.parentApp.switchForm("MAIN")

    def on_cancel(self):
        self.parentApp.switchForm("MAIN")


class UserMenu(npyscreen.ActionPopup):
    def create(self):
        self.userlist = self.add(npyscreen.TitleMultiSelect,
                                 values=pd.get_chat('user', 'list'),
                                 name="User select",
                                 scroll_exit=True)

    def on_ok(self):
        if self.userlist.get_selected_objects() == None:
            usrlist = []
        else:
            usrlist = self.userlist.get_selected_objects()
        for user in usrlist:
            if user == 'DUTY_OPS':
                usrlist.pop(usrlist.index('DUTY_OPS'))
                user = pd.get_chat('user', 'duty')
                usrlist.append(user)
        self.parentApp.selected_userlist = usrlist
        if self.parentApp.mainform.messageform.entry_widget.value is not None:
            self.parentApp.mainform.grub_the_data()
        self.parentApp.switchForm("MAIN")

    def on_cancel(self):
        self.parentApp.switchForm("MAIN")


class Confirmation(npyscreen.ActionPopup):
    DEFAULT_LINES = 18
    DEFAULT_COLUMNS = 80
    SHOW_ATX = 40
    SHOW_ATY = 10

    def create(self):
        self.chatlist = self.parentApp.selected_chatlist
        self.updatebut = self.add(Button, name='Get data', when_pressed_function=self.upd, value=True)
        self.user_preview = self.add(Preview_Window, name='Selected Users', max_height=5, editable=False)
        self.chat_preview = self.add(Preview_Window, name='Selected Chats', max_height=5, editable=False)

    def upd(self):
        if self.updatebut.value == True:
            self.chat_preview.entry_widget.value = str(self.parentApp.selected_chatlist)
            self.user_preview.entry_widget.value = str(self.parentApp.selected_userlist)
            self.display()

    def on_ok(self):
        chatlist = self.parentApp.selected_chatlist
        id = pd.get_chat('chat', 'send', chatlist)
        if self.parentApp.pasteflag == True:
            send = pd.send_message(self.parentApp.mainform.messageform.entry_widget.value, id, 'attach')
        else:
            send = pd.send_message(self.parentApp.mainform.messageform.entry_widget.value, id)
        if send == '200':
            pass
        self.parentApp.switchForm("MAIN")

    def on_cancel(self):
        self.parentApp.switchForm("MAIN")


class NOCTool(npyscreen.FormBaseNew):
    def __init__(self, name=None, parentApp=None, framed=None, help=None, color='FORMDEFAULT',
                 widget_list=None, cycle_widgets=False, *args, **keywords):
        super().__init__(name, parentApp, framed, help, color, widget_list, cycle_widgets, args, keywords)
        self.message_gen = None

    def create(self):
        handlers_dict = {
            ord('?'): self.faq,
            ord('r'): self.resolve,
        }
        self.add_handlers(handlers_dict)
        self.alertdict = pd.get_alerts()
        self.values = self.alertdict.get('alerts')
        self.add(npyscreen.TitleFixedText, name="This tool need a rework")
        self.button = self.add(Ackbutton, max_height=2, values=['On', 'Off'], name="Autoack", scroll_exit=True)
        self.add(npyscreen.TitleFixedText, max_height=2, name="Duty OPS Today is: {}".format(pd.who_duty()))
        self.pdinfo = self.add(PDinfo, name='alerts in PD', values=self.values, max_height=10, scroll_exit=True)
        self.updbutton = self.add(Button, name='Update', when_pressed_function=self.update_data)
        self.resolve_all = self.add(Button, name='Resolve all Alerts', rely=18, relx=25, when_pressed_function=self.resolve_all)
        self.chat = self.add(Button, name='Select Chat(s)', rely=20, when_pressed_function=self.select_chat)
        self.user = self.add(Button, name="Select User(s)", rely=20, relx=25, when_pressed_function=self.select_user)
        #self.action = self.add(Button, name='Action', rely=20, relx=45, when_pressed_function=self.select_action)
        self.messageform = self.add(Preview_Window, name='Prewiev the message', max_height=10)
        self.grubbutton = self.add(Button, name='Generate message', when_pressed_function=self.grub_the_data)
        self.copy_to_clipboard_button = self.add(Button, name='Copy to clipboard', when_pressed_function=self.copy_to_clipboard)
        self.sendbutton = self.add(Button, name='SEND MESSAGE', relx=120, when_pressed_function=self.confirm_send)
        self.how_exited_handers[npyscreen.wgwidget.EXITED_ESCAPE] = self.exit_app

    def while_waiting(self):
        self.update_data()

    def select_chat(self):
        self.parentApp.switchForm("CHAT")

    def select_user(self):
        self.parentApp.switchForm("USER")

    def select_action(self):
        self.parentApp.switchForm("ACTION")

    def confirm_send(self):
        self.parentApp.switchForm("CONFIRM")

    def exit_app(self):
        self.parentApp.setNextForm(None)
        self.editing = False

    def faq(self, key):
        npyscreen.notify_confirm('? -- this message\n'
                                 'r -- resolve chosen incident')

    def resolve(self, key):
        try:
            index = self.pdinfo.value[0]
            alert_id = self.alertdict.get('id')[index]
            resolve = pd.resolve(alert_id)
            if resolve == 200:
                npyscreen.notify_confirm('Succsess')
                self.update_data()
        except IndexError:
            npyscreen.notify_confirm("There is no alert chosen, or no alerts in PD", editw=10)

    def resolve_all(self):
        try:
            alerts = self.alertdict.get('id')
            for alert in alerts:
                pd.resolve(alert)
            npyscreen.notify_confirm('ALL ALERTS RESOLVED', 5)
            self.update_data()
        except IndexError:
          npyscreen.notify_confirm("There is no alert chosen, or no alerts in PD", editw=10)

    def update_data(self):
        self.alertdict = pd.get_alerts()
        self.pdinfo.values = self.alertdict.get('alerts')
        self.pdinfo.display()
        self.updbutton.value = False

    def copy_to_clipboard(self):
        copied_text = pyperclip.copy(self.message_gen)
        npyscreen.notify_confirm('Copied')

    def grub_the_data(self):
        if self.pdinfo.value != []:
            # self.parentApp.switchForm("SECOND")
            index = self.pdinfo.value[0]
            alert = pd.get_current_alert(self.alertdict.get('id')[index])
            self.parentApp.actionmenu.host.entry_widget.value = alert.get('hostname')
#            if alert.get('hostname') == 'Graphite':
#
#                npyscreen.notify_confirm('Source is Graphite actions is impossible', title='Error')
#            else:
#                print(self.parentApp.the_alert)
#                with open('inventory/hosts', 'w+') as f:
#                    ready_host = ansiblelib.convert_hosts(str(alert.get('hostname')))
#                    yaml = 'all:\n  hosts:\n    {}:'.format(ready_host)
#                    f.write(yaml)
#                    f.close()
            host = 'Хост/Источник: {} \n'.format(alert.get('hostname'))
            check = 'Чек: {}\n'.format(alert.get('checkname'))
            self.output = 'Вывод: \n{}'.format(alert.get('output'))
            if self.parentApp.pasteflag == True:
                file = open('output.txt', 'w+')
                file.write(self.output)
                logging.debug(file)
                print(file.read())
                file.close()
                self.output = 'Output in the file below'
                # self.output = 'Вывод: \n\/paste [output]\n{}'.format(alert.get('output'))

            self.message_gen = host + check + self.output
            if self.parentApp.selected_userlist is not None:
                self.message_gen = pd.unpack(self.parentApp.selected_userlist) + '\n' + self.message_gen
            self.messageform.entry_widget.value = self.message_gen
            self.messageform.display()



if __name__ == "__main__":
    logging.basicConfig(filename='TUI.log', level=logging.DEBUG)
    signal.signal(signal.SIGINT, handler)
    mp.set_start_method("spawn")

    npyscreen.wrapper(MainScreen().run())
