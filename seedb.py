import sqlite3

# 连接到 .db 文件
conn = sqlite3.connect('site.db')

# 创建游标对象
cursor = conn.cursor()

# 执行 SQL 查询
cursor.execute()

# 获取查询结果
rows = cursor.fetchall()
for row in rows:
    print(row)

# 关闭连接
conn.close()