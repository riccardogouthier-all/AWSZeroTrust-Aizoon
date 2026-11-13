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
    for index,(role,script,label) in enumerate(captured):
     if "python3 <<'PY'\n" in script:
      code=script.split("python3 <<'PY'\n",1)[1].split('\nPY\n',1)[0]
      compile(code,label,'exec')
     (Path('evidence')/f'cyber-payload-{index}-{role}.sh').write_text(script,encoding='utf-8',newline='\n')
    assert any('/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf' in script for _,script,_ in captured)
    assert any('bt_waf_audit' in script for role,script,_ in captured if role=='waf')
    assert all('wazuh-install.sh -a' not in script for _,script,_ in captured)
    print('PASS: seven payloads, Python syntax, cyber rule/input provenance, no reinstall.')


if __name__ == "__main__":
    main()
