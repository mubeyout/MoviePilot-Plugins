import sqlite3, json
conn = sqlite3.connect('/config/user.db')
cur = conn.cursor()

# 1. 确保 MediaVerse 在 UserInstalledPlugins 列表中
cur.execute("SELECT value FROM SystemConfig WHERE key = 'UserInstalledPlugins'")
r = cur.fetchone()
if r:
    plugins = json.loads(r[0])
    if 'MediaVerse' not in plugins:
        plugins.append('MediaVerse')
        cur.execute("UPDATE SystemConfig SET value = ? WHERE key = 'UserInstalledPlugins'", (json.dumps(plugins),))
        print('MediaVerse added to UserInstalledPlugins')
    else:
        print('MediaVerse already in UserInstalledPlugins')

# 2. 设置 MediaVerse 插件为启用状态
cur.execute("SELECT value FROM SystemConfig WHERE key = 'plugin.MediaVerse'")
r = cur.fetchone()
if r:
    config = json.loads(r[0])
    config['enabled'] = True
    cur.execute("UPDATE SystemConfig SET value = ? WHERE key = 'plugin.MediaVerse'", (json.dumps(config),))
    print('MediaVerse enabled')
else:
    # 创建默认配置并启用
    default_config = json.dumps({"enabled": True, "api_base": "http://10.0.0.1:8922"})
    cur.execute("INSERT INTO SystemConfig (key, value) VALUES ('plugin.MediaVerse', ?)", (default_config,))
    print('MediaVerse config created and enabled')

conn.commit()
conn.close()
print('Done')
