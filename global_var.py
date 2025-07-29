global_var = 10

# 定义函数
def print_global_var():
    print("全局变量的值：", global_var)

# 定义修改全局变量的函数
def change_global_var(new_value):
    global global_var
    global_var = new_value