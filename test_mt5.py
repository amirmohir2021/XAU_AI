import MetaTrader5 as mt5

if not mt5.initialize():
    print("MT5 ga ulanishda xatolik!")
    print(mt5.last_error())
    quit()

print("MT5 muvaffaqiyatli ulandi!")

account = mt5.account_info()

if account:
    print("Login:", account.login)
    print("Server:", account.server)
    print("Balance:", account.balance)
else:
    print("Account ma'lumotini olib bo'lmadi.")

mt5.shutdown()