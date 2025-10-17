# scripts/convert.py
import yaml
import requests
import os

# --- 配置项 ---
SOURCE_YAML_URL = 'https://raw.githubusercontent.com/liandu2024/little/refs/heads/main/yaml/clash-fallback-all.yaml'
OUTPUT_INI_FILE = 'clash-template.ini' # 输出的ini文件名，将保存在仓库根目录

# --- 模板头部和尾部 ---
INI_HEADER = """
; === OpenClash 自动转换订阅模板 ===
; 源文件: {source_url}
; 最后更新时间: {update_time}
; 本模板由 GitHub Actions 自动生成

; 1、域名规则集
ruleset=国外,https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Global/Global.list
ruleset=国内,[]FINAL
""".lstrip()

INI_POLICY_GROUPS_HEADER = "\n; 2、策略组 - 业务分流 (为每个域名组创建独立的策略选项)"
INI_NODE_GROUPS_HEADER = "\n; 3、节点策略组 - 按地区筛选与策略整合"
INI_FOOTER = """
; 4、启用规则集
enable_rule_generator=true
overwrite_original_rules=true
""".lstrip()

# --- 主逻辑 ---
def fetch_yaml_data(url):
    """从URL获取并解析YAML数据"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return yaml.safe_load(response.text)
    except Exception as e:
        print(f"错误: 无法获取或解析YAML文件. {e}")
        return None

def generate_rulesets(data):
    """从rule-providers生成ruleset"""
    rulesets = []
    providers = data.get('rule-providers', {})
    for name, details in providers.items():
        # 我们只关心域名规则，并且优先使用.list格式的规则
        name_key = name.split(' ')[0] # 'ChatGPT / Domain' -> 'ChatGPT'
        url = details.get('url', '').replace('gh-proxy.com/raw.githubusercontent.com', 'raw.githubusercontent.com').replace('gh-proxy.com/github.com', 'raw.githubusercontent.com')
        
        # 将.mrs链接尝试替换为常见的.list链接 (这是一个简化逻辑，可能需要按需调整)
        if url.endswith('.mrs'):
            # 示例替换逻辑，可扩展
            if 'geosite/openai' in url:
                url = 'https://raw.githubusercontent.com/metacubex/meta-rules-dat/meta/geo/geosite/openai.list'
            elif 'geosite/netflix' in url:
                url = 'https://raw.githubusercontent.com/metacubex/meta-rules-dat/meta/geo/geosite/netflix.list'
            # ...可以添加更多mrs到list的转换规则
            
        if 'Domain' in name and url:
             rulesets.append(f"ruleset={name_key},{url}")

    # 去重并排序
    return sorted(list(set(rulesets)))

def generate_policy_groups(data):
    """从proxy-groups生成业务分流策略组"""
    groups = []
    base_policy = "`select`[]DIRECT`[]所有-手动`[]所有-自动`[]香港-故转`[]台湾-故转`[]日本-故转`[]新加坡-故转`[]韩国-故转`[]美国-故转`[]英国-故转`[]其他-故转`[]REJECT"
    
    proxy_groups = data.get('proxy-groups', [])
    for group in proxy_groups:
        group_name = group.get('name')
        # 仅为那些使用了默认分流策略的组创建规则
        if group_name and group.get('type') == 'select' and '<<: *default' in str(group):
             groups.append(f"custom_proxy_group={group_name}{base_policy}")

    # 添加一些在rules里但可能不在proxy-groups里的组
    special_groups = ['Block', 'Test']
    for group_name in special_groups:
        if group_name == 'Block':
            groups.append(f"custom_proxy_group={group_name}`select`[]REJECT")
        else:
            groups.append(f"custom_proxy_group={group_name}{base_policy}")

    return sorted(list(set(groups)))

def generate_node_groups():
    """生成固定的节点分组和Fallback策略组"""
    # 这部分内容是固定的，直接从之前验证过的模板复制
    return """
; --- 全局节点组 ---
custom_proxy_group=所有-手动`select`.*`exclude-filter=^(DIRECT|REJECT)$
custom_proxy_group=所有-自动`url-test`.*`http://www.gstatic.com/generate_204`300,5,50`exclude-filter=^(DIRECT|REJECT)$

; --- 香港组 (手动->自动->故障转移) ---
custom_proxy_group=香港-故转`fallback`[]香港-手动`[]香港-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=香港-手动`select`(广港|香港|HK|Hong Kong|🇭🇰|HongKong)
custom_proxy_group=香港-自动`url-test`(广港|香港|HK|Hong Kong|🇭🇰|HongKong)`http://www.gstatic.com/generate_204`300,5,50

; --- 台湾组 (手动->自动->故障转移) ---
custom_proxy_group=台湾-故转`fallback`[]台湾-手动`[]台湾-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=台湾-手动`select`(广台|台湾|台灣|TW|Tai Wan|🇹🇼|🇨🇳|TaiWan|Taiwan)
custom_proxy_group=台湾-自动`url-test`(广台|台湾|台灣|TW|Tai Wan|🇹🇼|🇨🇳|TaiWan|Taiwan)`http://www.gstatic.com/generate_204`300,5,50

; --- 日本组 (手动->自动->故障转移) ---
custom_proxy_group=日本-故转`fallback`[]日本-手动`[]日本-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=日本-手动`select`(广日|日本|JP|川日|东京|大阪|泉日|埼玉|沪日|深日|🇯🇵|Japan)
custom_proxy_group=日本-自动`url-test`(广日|日本|JP|川日|东京|大阪|泉日|埼玉|沪日|深日|🇯🇵|Japan)`http://www.gstatic.com/generate_204`300,5,50

; --- 新加坡组 (手动->自动->故障转移) ---
custom_proxy_group=新加坡-故转`fallback`[]新加坡-手动`[]新加坡-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=新加坡-手动`select`(广新|新加坡|SG|坡|狮城|🇸🇬|Singapore)
custom_proxy_group=新加坡-自动`url-test`(广新|新加坡|SG|坡|狮城|🇸🇬|Singapore)`http://www.gstatic.com/generate_204`300,5,50

; --- 韩国组 (手动->自动->故障转移) ---
custom_proxy_group=韩国-故转`fallback`[]韩国-手动`[]韩国-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=韩国-手动`select`(广韩|韩国|韓國|KR|首尔|春川|🇰🇷|Korea)
custom_proxy_group=韩国-自动`url-test`(广韩|韩国|韓國|KR|首尔|春川|🇰🇷|Korea)`http://www.gstatic.com/generate_204`300,5,50

; --- 美国组 (手动->自动->故障转移) ---
custom_proxy_group=美国-故转`fallback`[]美国-手动`[]美国-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=美国-手动`select`(广美|US|美国|纽约|波特兰|达拉斯|俄勒|凤凰城|费利蒙|洛杉|圣何塞|圣克拉|西雅|芝加|🇺🇸|United States)
custom_proxy_group=美国-自动`url-test`(广美|US|美国|纽约|波特兰|达拉斯|俄勒|凤凰城|费利蒙|洛杉|圣何塞|圣克拉|西雅|芝加|🇺🇸|United States)`http://www.gstatic.com/generate_204`300,5,50

; --- 英国组 (手动->自动->故障转移) ---
custom_proxy_group=英国-故转`fallback`[]英国-手动`[]英国-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=英国-手动`select`(英国|英|伦敦|UK|United Kingdom|🇬🇧|London)
custom_proxy_group=英国-自动`url-test`(英国|英|伦敦|UK|United Kingdom|🇬🇧|London)`http://www.gstatic.com/generate_204`300,5,50

; --- 其他地区组 (手动->自动->故障转移) ---
custom_proxy_group=其他-故转`fallback`[]其他-手动`[]其他-自动`http://www.gstatic.com/generate_204`300,5
custom_proxy_group=其他-手动`select`.*`exclude-filter=^(DIRECT|REJECT|广港|香港|HK|Hong Kong|🇭🇰|HongKong|广台|台湾|台灣|TW|Tai Wan|🇹🇼|🇨🇳|TaiWan|Taiwan|广日|日本|JP|川日|东京|大阪|泉日|埼玉|沪日|深日|🇯🇵|Japan|广新|新加坡|SG|坡|狮城|🇸🇬|Singapore|广韩|韩国|韓國|KR|首尔|春川|🇰🇷|Korea|广美|US|美国|纽约|波特兰|达拉斯|俄勒|凤凰城|费利蒙|洛杉|圣何塞|圣克拉|西雅|芝加|🇺🇸|United States|英国|UK|United Kingdom|伦敦|英|London|🇬🇧)$
custom_proxy_group=其他-自动`url-test`.*`http://www.gstatic.com/generate_204`300,5,50`exclude-filter=^(DIRECT|REJECT|广港|香港|HK|Hong Kong|🇭🇰|HongKong|广台|台湾|台灣|TW|Tai Wan|🇹🇼|🇨🇳|TaiWan|Taiwan|广日|日本|JP|川日|东京|大阪|泉日|埼玉|沪日|深日|🇯🇵|Japan|广新|新加坡|SG|坡|狮城|🇸🇬|Singapore|广韩|韩国|韓國|KR|首尔|春川|🇰🇷|Korea|广美|US|美国|纽约|波特兰|达拉斯|俄勒|凤凰城|费利蒙|洛杉|圣何塞|圣克拉|西雅|芝加|🇺🇸|United States|英国|UK|United Kingdom|伦敦|英|London|🇬🇧)$
""".strip()


if __name__ == "__main__":
    from datetime import datetime, timezone, timedelta
    
    print("开始执行转换...")
    data = fetch_yaml_data(SOURCE_YAML_URL)
    
    if data:
        # 获取东八区时间
        utc_now = datetime.now(timezone.utc)
        cst_now = utc_now.astimezone(timezone(timedelta(hours=8)))
        update_time_str = cst_now.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        # 生成各个部分
        header_part = INI_HEADER.format(source_url=SOURCE_YAML_URL, update_time=update_time_str)
        rulesets_part = "\n".join(generate_rulesets(data))
        policy_groups_part = INI_POLICY_GROUPS_HEADER + "\n" + "\n".join(generate_policy_groups(data))
        node_groups_part = INI_NODE_GROUPS_HEADER + "\n" + generate_node_groups()
        
        # 拼接最终INI内容
        final_ini_content = f"{header_part}\n{rulesets_part}\n{policy_groups_part}\n{node_groups_part}\n{INI_FOOTER}"
        
        # 写入文件
        # GITHUB_WORKSPACE是GitHub Actions提供的环境变量，指向仓库根目录
        workspace = os.environ.get('GITHUB_WORKSPACE', '.')
        output_path = os.path.join(workspace, OUTPUT_INI_FILE)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_ini_content)
        
        print(f"成功！转换后的模板已保存到: {output_path}")
