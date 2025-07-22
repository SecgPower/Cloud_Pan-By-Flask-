from app import create_app

app = create_app()

if __name__ == '__main__':
    # 打印所有注册的路由
    print("已注册的路由:")
    for rule in app.url_map.iter_rules():
        print(f"{rule}")
    app.run(debug=app.config['DEBUG'], host=app.config['HOST'], port=app.config['PORT'])
