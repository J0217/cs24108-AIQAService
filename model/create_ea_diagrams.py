# -*- coding: utf-8 -*-
"""
EA 16 自动化脚本（放大字体版）
- 元素字号 22（微软雅黑），Artifact/Note 较小
- 布局紧凑化，配合 IMG_SCALE_FACTOR3=150 导出，最终 1800-2400px 宽
- StateNode 空名会被 EA 自动改为 "Pseudostate"，导出前在数据库清空
"""
import win32com.client
import pythoncom
import os
import shutil
import sqlite3
import time
import winreg

PROJECT_PATH = r"d:\cs24108-AIQAService\model\AIQAService-Plan.qea"
ASSETS_PATH = r"d:\cs24108-AIQAService\docs\assets"
BASE_QEA = r"C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.qea"

FONT = "Microsoft YaHei"
FS_ELEM = 22      # 主要元素字号
FS_ART = 16       # 部署工件字号
FS_NOTE = 14      # 备注字号
SCALE_PCT = 150   # 导出缩放百分比（临时修改注册表）

TARGETS = {
    "图 2-1 项目组织与接口协作关系": "fig-2-1-org.png",
    "图 7-1 dev/test/prod 部署拓扑": "fig-7-1-deploy.png",
    "图 12-1 分支与配置管理流程": "fig-12-1-branch.png",
}


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def add_package(parent, name):
    pkg = parent.Packages.AddNew(name, "Package")
    pkg.Update()
    parent.Packages.Refresh()
    print(f"  创建包: {name}")
    return pkg


def add_element(package, name, etype, subtype=None, notes=None):
    elem = package.Elements.AddNew(name, etype)
    if subtype is not None:
        elem.Subtype = subtype
    if notes:
        elem.Notes = notes
    elem.Update()
    package.Elements.Refresh()
    print(f"    元素: {name or etype} ({etype})")
    return elem


def place(diagram, element, left, right, top, bottom, fontsize=FS_ELEM):
    """position 字符串放置元素（EA 内部将 top/bottom 转负值，y 向下增长）"""
    pos = f"l={left};r={right};t={top};b={bottom};"
    dob = diagram.DiagramObjects.AddNew(pos, "")
    dob.ElementID = element.ElementID
    dob.fontSize = fontsize
    dob.fontName = FONT
    dob.Update()
    diagram.DiagramObjects.Refresh()
    return dob


def add_connector(source, dest, ctype, name=""):
    conn = source.Connectors.AddNew(name, ctype)
    conn.ClientID = source.ElementID
    conn.SupplierID = dest.ElementID
    conn.Update()
    source.Connectors.Refresh()
    print(f"    连接: {source.Name or ctype} -> {dest.Name or ctype} [{ctype}] {name}")
    return conn


def set_export_scale(pct):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Sparx Systems\EA400\EA\OPTIONS", 0, winreg.KEY_ALL_ACCESS)
    old_val, old_type = winreg.QueryValueEx(key, "IMG_SCALE_FACTOR3")
    winreg.SetValueEx(key, "IMG_SCALE_FACTOR3", 0, winreg.REG_DWORD, int(pct))
    winreg.CloseKey(key)
    print(f"导出缩放: {old_val}% -> {pct}%")
    return int(old_val)


def restore_scale(old_val):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Sparx Systems\EA400\EA\OPTIONS", 0, winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(key, "IMG_SCALE_FACTOR3", 0, winreg.REG_DWORD, int(old_val))
    winreg.CloseKey(key)
    print(f"导出缩放恢复: {old_val}%")


def export_all(ea, out_dir):
    proj = ea.GetProjectInterface()
    from PIL import Image
    results = {}
    for mi in range(ea.Models.Count):
        model = ea.Models.GetAt(mi)
        for pi in range(model.Packages.Count):
            pkg = model.Packages.GetAt(pi)
            for di in range(pkg.Diagrams.Count):
                dia = pkg.Diagrams.GetAt(di)
                if dia.Name in TARGETS:
                    out = os.path.join(out_dir, TARGETS[dia.Name])
                    result = proj.PutDiagramImageToFile(dia.DiagramGUID, out, 1)
                    if result and os.path.exists(out):
                        img = Image.open(out)
                        img.save(out, dpi=(300, 300))
                        print(f"  导出: {dia.Name} -> {out} ({img.size[0]}x{img.size[1]} px)")
                        results[dia.Name] = img.size
    return results


def clear_pseudostate_names(db_path):
    """EA 自动将空名 StateNode 命名为 Pseudostate，清空以免渲染出多余小字"""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("UPDATE t_object SET Name='' WHERE Object_Type='StateNode'")
    n = cur.rowcount
    con.commit()
    con.close()
    print(f"清空 StateNode 名称: {n} 个")


def run_export(scale_pct, old_scale):
    """启动 EA 导出全部目标图，结束后恢复缩放"""
    pythoncom.CoInitialize()
    try:
        ea = win32com.client.Dispatch("EA.Repository")
        ea.OpenFile(PROJECT_PATH)
        set_export_scale(scale_pct)
        try:
            export_all(ea, ASSETS_PATH)
        finally:
            ea.Exit()
            time.sleep(2)
            restore_scale(old_scale)
    finally:
        pythoncom.CoUninitialize()


def main():
    ensure_dir(ASSETS_PATH)

    print("=== 重建模型 ===")
    tmp = PROJECT_PATH + ".tmp"
    shutil.copy2(BASE_QEA, tmp)
    if os.path.exists(PROJECT_PATH):
        try:
            os.remove(PROJECT_PATH)
        except OSError:
            pass
    os.replace(tmp, PROJECT_PATH)

    pythoncom.CoInitialize()
    ea = win32com.client.Dispatch("EA.Repository")
    ea.OpenFile(PROJECT_PATH)
    print(f"EA 版本: {ea.LibraryVersion}")

    root_model = ea.Models.GetAt(0)
    root_model.Name = "AIQAService"
    root_model.Update()

    pkg01 = add_package(root_model, "01 需求")
    pkg02 = add_package(root_model, "02 设计")
    pkg03 = add_package(root_model, "03 部署")
    pkg04 = add_package(root_model, "04 配置")

    # ============================================================
    # 图 2-1 组件图（布局宽约 1460）
    # ============================================================
    print("=== 图 2-1 组件图 ===")
    diagram21 = pkg02.Diagrams.AddNew("图 2-1 项目组织与接口协作关系", "Component")
    diagram21.Update()
    pkg02.Diagrams.Refresh()

    actor_mini = add_element(pkg02, "小程序用户", "Actor")
    actor_api = add_element(pkg02, "API调用方", "Actor")
    comp_a = add_element(pkg02, "A-用户管理", "Component")
    comp_b = add_element(pkg02, "B-对话管理", "Component")
    comp_c = add_element(pkg02, "C-AI引擎", "Component")
    comp_d = add_element(pkg02, "D-公告管理", "Component")
    comp_e = add_element(pkg02, "E-多端接入", "Component")

    place(diagram21, actor_mini, 60, 200, 50, 230)
    place(diagram21, actor_api, 60, 200, 530, 710)
    place(diagram21, comp_e, 420, 700, 300, 480)
    place(diagram21, comp_a, 1120, 1400, 40, 140)
    place(diagram21, comp_b, 1120, 1400, 240, 340)
    place(diagram21, comp_c, 1120, 1400, 440, 540)
    place(diagram21, comp_d, 1120, 1400, 640, 740)

    add_connector(actor_mini, comp_e, "Association", "使用小程序")
    add_connector(actor_api, comp_e, "Association", "调用 /api/v1/*  HTTPS + X-API-Key")
    add_connector(comp_e, comp_a, "Dependency", "/api/auth/*  HTTPS + JWT")
    add_connector(comp_e, comp_b, "Dependency", "/api/chat/*  HTTPS + JWT")
    add_connector(comp_e, comp_c, "Dependency", "回复生成(经B)")
    add_connector(comp_e, comp_d, "Dependency", "/api/announcement/*  HTTPS + JWT")
    diagram21.Update()

    # ============================================================
    # 图 7-1 部署图（布局宽约 1560）
    # ============================================================
    print("=== 图 7-1 部署图 ===")
    diagram71 = pkg03.Diagrams.AddNew("图 7-1 dev/test/prod 部署拓扑", "Deployment")
    diagram71.Update()
    pkg03.Diagrams.Refresh()

    node_phone = add_element(pkg03, "用户手机", "Node")
    node_wx = add_element(pkg03, "微信平台", "Node")
    node_dev = add_element(pkg03, "开发机", "Node")
    node_test = add_element(pkg03, "测试运行", "Node")
    node_prod = add_element(pkg03, "生产服务器（规划）", "Node")

    art_mini = add_element(pkg03, "微信小程序\n(游客模式/测试号)", "Artifact")
    art_wx = add_element(pkg03, "wx.login 换取 code", "Artifact")
    art_flask = add_element(pkg03, "Flask app.py\nPython 3.14.6 :5000", "Artifact")
    art_db = add_element(pkg03, "SQLite\ninstance/ai_qa_service.db", "Artifact")
    art_ut = add_element(pkg03, "Python unittest\n临时 SQLite / test_client", "Artifact")
    art_gunicorn = add_element(pkg03, "gunicorn + PostgreSQL\n【未部署】", "Artifact")

    place(diagram71, node_phone, 60, 380, 40, 280)
    place(diagram71, node_wx, 1180, 1500, 40, 280)
    place(diagram71, node_dev, 60, 380, 500, 880)
    place(diagram71, node_test, 720, 1040, 500, 780)
    place(diagram71, node_prod, 60, 380, 1080, 1460)

    place(diagram71, art_mini, 90, 350, 110, 190, fontsize=FS_ART)
    place(diagram71, art_wx, 1210, 1470, 110, 190, fontsize=FS_ART)
    place(diagram71, art_flask, 90, 350, 560, 640, fontsize=FS_ART)
    place(diagram71, art_db, 90, 350, 690, 770, fontsize=FS_ART)
    place(diagram71, art_ut, 750, 1010, 550, 630, fontsize=FS_ART)
    place(diagram71, art_gunicorn, 90, 350, 1140, 1220, fontsize=FS_ART)

    add_connector(node_phone, node_dev, "Association", "http://局域网IP:5000")
    add_connector(node_dev, node_wx, "Association", "HTTPS")
    add_connector(node_dev, node_prod, "Dependency", "规划，未部署")
    diagram71.Update()

    # ============================================================
    # 图 12-1 活动图
    # ============================================================
    print("=== 图 12-1 活动图 ===")
    diagram121 = pkg04.Diagrams.AddNew("图 12-1 分支与配置管理流程", "Activity")
    diagram121.Update()
    pkg04.Diagrams.Refresh()

    initial = add_element(pkg04, "", "StateNode", subtype=100)
    act_commit = add_element(pkg04, "在 feature/2024213575-duoduan 提交", "Action")
    act_pr = add_element(pkg04, "发起 PR", "Action")
    act_review = add_element(pkg04, "组员评审", "Action")
    dec1 = add_element(pkg04, "评审通过？", "Decision")
    act_return = add_element(pkg04, "返回修改", "Action")
    act_merge_dev = add_element(pkg04, "合入 develop", "Action")
    act_test = add_element(pkg04, "回归测试 7 条用例", "Action")
    dec2 = add_element(pkg04, "通过？", "Decision")
    act_merge_main = add_element(pkg04, "合入 main", "Action")
    act_tag = add_element(pkg04, "打 tag lab1-plan-v1.0", "Action")
    final = add_element(pkg04, "", "StateNode", subtype=101)
    note = add_element(pkg04, "备注", "Note",
                       notes="当前仓库仅 main 分支，流程为本次实验要建立的基线")

    place(diagram121, initial, 660, 740, 30, 90)
    place(diagram121, act_commit, 430, 950, 140, 230)
    place(diagram121, act_pr, 430, 950, 290, 380)
    place(diagram121, act_review, 430, 950, 440, 530)
    place(diagram121, dec1, 560, 820, 580, 690)
    place(diagram121, act_merge_dev, 430, 950, 750, 840)
    place(diagram121, act_test, 430, 950, 900, 990)
    place(diagram121, dec2, 560, 820, 1040, 1150)
    place(diagram121, act_merge_main, 430, 950, 1210, 1300)
    place(diagram121, act_tag, 430, 950, 1360, 1450)
    place(diagram121, final, 660, 740, 1510, 1570)
    place(diagram121, act_return, 100, 340, 750, 840)
    place(diagram121, note, 1120, 1620, 140, 280, fontsize=FS_NOTE)

    add_connector(initial, act_commit, "Transition")
    add_connector(act_commit, act_pr, "Transition")
    add_connector(act_pr, act_review, "Transition")
    add_connector(act_review, dec1, "Transition")
    add_connector(dec1, act_merge_dev, "Transition", "是")
    add_connector(act_merge_dev, act_test, "Transition")
    add_connector(act_test, dec2, "Transition")
    add_connector(dec2, act_merge_main, "Transition", "是")
    add_connector(act_merge_main, act_tag, "Transition")
    add_connector(act_tag, final, "Transition")
    add_connector(dec1, act_return, "Transition", "否")
    add_connector(dec2, act_return, "Transition", "否")
    add_connector(act_return, act_pr, "Transition")
    add_connector(note, act_commit, "NoteLink")
    diagram121.Update()

    # ============================================================
    # 导出：先导一次，清 Pseudostate 名，再重导
    # ============================================================
    print("=== 导出 PNG ===")
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Sparx Systems\EA400\EA\OPTIONS", 0, winreg.KEY_ALL_ACCESS)
    old_scale, _ = winreg.QueryValueEx(key, "IMG_SCALE_FACTOR3")
    winreg.CloseKey(key)

    try:
        set_export_scale(SCALE_PCT)
        export_all(ea, ASSETS_PATH)
    finally:
        ea.Exit()
        time.sleep(2)
        restore_scale(old_scale)
        pythoncom.CoUninitialize()

    clear_pseudostate_names(PROJECT_PATH)
    run_export(SCALE_PCT, old_scale)

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
