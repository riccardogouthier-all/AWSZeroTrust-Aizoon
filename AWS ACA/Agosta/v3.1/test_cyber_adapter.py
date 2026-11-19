"""Dry-run safety checks: generate all SSM payloads without contacting AWS."""

def main():
    from pathlib import Path
    from unittest.mock import patch
    import runpy
    import contextlib,io
    with patch("boto3.Session"):
        import ops
    captured=[]
    ops.send=lambda role,script,label:captured.append((role,script,label)) or label
    ops.wait=lambda *args:None
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path('apply_cyber.py',run_name='adapter_self_check')
    assert len(captured)==7
    full_siem = captured[-1][1]
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path('update_cyber_rules.py', run_name='__main__')
    assert [role for role, _, _ in captured[-2:]] == ["siem", "waf"]
    from update_cyber_rules import AUDIT_CLASSIFICATIONS, RULE, stage
    from xml.etree import ElementTree
    import re
    rules = ElementTree.fromstring(AUDIT_CLASSIFICATIONS).findall("rule")
    for rule, waf_id in zip(rules, ("942100", "941100", "10011", "10012", "10013", "10014", "10015"), strict=True):
        assert rule.findtext("if_sid") == "100100"
        assert re.search(rule.findtext("location"), "/opt/blue-team/logs/modsec_audit.log")
        assert re.search(rule.findtext("location"), "(waf) any->/opt/blue-team/logs/modsec_audit.log")
        assert re.search(rule.findtext("match"), f'bt_waf_audit {{"ruleId":"{waf_id}"}}')
        assert not re.search(rule.findtext("match"), f'bt_waf_audit {{"ruleId":"{waf_id}0"}}')
    assert stage("candidate", AUDIT_CLASSIFICATIONS) in full_siem
    assert stage("candidate", AUDIT_CLASSIFICATIONS) in captured[-2][1]
    assert stage("target", RULE) in captured[-1][1]
    assert 'logall_json' not in captured[-2][1]
    assert 'MODSEC_RULE_ENGINE=DetectionOnly' in captured[-1][1]
    for index,(role,script,label) in enumerate(captured):
     if "python3 <<'PY'\n" in script:
      code=script.split("python3 <<'PY'\n",1)[1].split('\nPY\n',1)[0]
      compile(code,label,'exec')
     (Path('evidence')/f'cyber-payload-{index}-{role}.sh').write_text(script,encoding='utf-8',newline='\n')
    assert any('/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf' in script for _,script,_ in captured)
    assert any('bt_waf_audit' in script for role,script,_ in captured if role=='waf')
    assert all('wazuh-install.sh -a' not in script for _,script,_ in captured)
    print('PASS: seven bootstrap payloads and two rules-only payloads.')


if __name__ == "__main__":
    main()
