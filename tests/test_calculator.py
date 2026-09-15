"""tests/test_calculator.py — Tests for Gold Value Calculator feature."""
import os
import re
import subprocess
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_calculator_component_structure():
    """components/5-calculator.html contains all necessary calculator elements and events."""
    calc_html_path = PROJECT_ROOT / "components" / "5-calculator.html"
    assert calc_html_path.exists(), "5-calculator.html must exist"
    content = calc_html_path.read_text(encoding="utf-8")

    assert 'id="calc-weight-input"' in content
    assert 'id="calc-unit-select"' in content
    assert 'value="baht"' in content
    assert 'value="gram"' in content
    assert 'value="salung"' in content
    assert 'value="kilogram"' in content

    # Result elements
    for res_id in [
        "result-gram",
        "result-baht",
        "result-bar-buy",
        "result-bar-sell",
        "result-jewelry-buy",
        "result-jewelry-sell",
    ]:
        assert f'id="{res_id}"' in content, f"Missing result element {res_id}"

    # Event handlers on input and select
    assert 'oninput="calculateGoldValue()"' in content
    assert 'onchange="calculateGoldValue()"' in content


def test_script_calculator_logic_rules():
    """js/script.js has calculateGoldValue, initGoldCalculator, and no login blockade."""
    script_path = PROJECT_ROOT / "js" / "script.js"
    assert script_path.exists(), "js/script.js must exist"
    content = script_path.read_text(encoding="utf-8")

    # Check function presence
    assert "function calculateGoldValue()" in content
    assert "function initGoldCalculator()" in content

    # Crucial fix: calculateGoldValue must NOT block guests with 'if (!window.isLoggedIn) return;'
    calc_fn_match = re.search(r"function calculateGoldValue\(\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", content)
    assert calc_fn_match is not None, "calculateGoldValue body found"
    calc_body = calc_fn_match.group(1)
    assert "if (!window.isLoggedIn) return;" not in calc_body, (
        "calculateGoldValue must not block guest users"
    )

    # Global exposures
    assert "window.initGoldCalculator = initGoldCalculator;" in content
    assert "window.calculateGoldValue = calculateGoldValue;" in content

    # Ensure fetchAndUpdatePriceBoard triggers calculateGoldValue
    assert "calculateGoldValue();" in content
    assert "window.latestThaiPrices = latestThaiPrices;" in content


def test_calculator_execution_node_simulation():
    """Simulate calculator execution in headless Node.js environment."""
    test_node_file = PROJECT_ROOT / "tests" / "run_node_calc_test.js"
    test_node_code = """
    const fs = require('fs');
    const elements = {};
    function getEl(id) {
        if (!elements[id]) {
            elements[id] = {
                id,
                value: '',
                textContent: '--',
                eventListeners: {},
                addEventListener: function(e, fn) { this.eventListeners[e] = fn; },
                removeEventListener: function(e, fn) { delete this.eventListeners[e]; }
            };
        }
        return elements[id];
    }
    const tableRows = [
        { querySelector: () => ({ textContent: '1 กรัม' }), style: {}, title: '', onclick: null },
        { querySelector: () => ({ textContent: '1 สลึง' }), style: {}, title: '', onclick: null },
        { querySelector: () => ({ textContent: '1 บาท' }), style: {}, title: '', onclick: null }
    ];

    global.document = {
        getElementById: getEl,
        querySelectorAll: (sel) => (sel.includes('.weight-table') ? tableRows : []),
        addEventListener: () => {}
    };
    global.window = { isLoggedIn: false }; // Guest user
    global.localStorage = {
        _data: {},
        getItem: function(k) { return this._data[k] || null; },
        setItem: function(k, v) { this._data[k] = String(v); }
    };
    global.setInterval = () => ({ unref: () => {} });
    global.setTimeout = () => ({ unref: () => {} });
    global.clearInterval = () => {};
    global.clearTimeout = () => {};

    const code = fs.readFileSync('js/script.js', 'utf8');
    // Remove await from top-level so eval works in CJS
    const sanitized = code.replace(/await /g, '');
    eval(sanitized);

    // Initial state: input 1 baht
    getEl('calc-weight-input').value = '1';
    getEl('calc-unit-select').value = 'baht';

    // 1. Calculate with default fallback
    calculateGoldValue();
    const res1 = {
        gram: getEl('result-gram').textContent,
        baht: getEl('result-baht').textContent,
        barBuy: getEl('result-bar-buy').textContent,
        barSell: getEl('result-bar-sell').textContent
    };
    if (res1.gram !== '15.244' || res1.baht !== '1.000' || !res1.barBuy.includes('67,200')) {
        console.error('Test 1 Failed:', res1);
        process.exit(1);
    }

    // 2. Calculate 1 gram
    getEl('calc-weight-input').value = '1';
    getEl('calc-unit-select').value = 'gram';
    calculateGoldValue();
    const res2 = {
        gram: getEl('result-gram').textContent,
        baht: getEl('result-baht').textContent
    };
    if (res2.gram !== '1.000' || res2.baht !== '0.066') {
        console.error('Test 2 Failed:', res2);
        process.exit(2);
    }

    // 3. Test empty/negative input
    getEl('calc-weight-input').value = '';
    calculateGoldValue();
    if (getEl('result-gram').textContent !== '0.000' || getEl('result-baht').textContent !== '0.000') {
        console.error('Test 3 Failed: empty input did not reset to 0');
        process.exit(3);
    }

    // 4. Test live prices update
    window.latestThaiPrices = {
        bar_buy: 70000,
        bar_sell: 70200,
        ornament_buy: 68000,
        ornament_sell: 70500
    };
    getEl('calc-weight-input').value = '2';
    getEl('calc-unit-select').value = 'baht';
    calculateGoldValue();
    if (!getEl('result-bar-buy').textContent.includes('140,000')) {
        console.error('Test 4 Failed: live price 2 baht not 140,000', getEl('result-bar-buy').textContent);
        process.exit(4);
    }

    // 5. Test initGoldCalculator and table row clicks
    initGoldCalculator();
    // Simulate click on row 1 (1 สลึง)
    tableRows[1].onclick();
    if (getEl('calc-weight-input').value !== 1 || getEl('calc-unit-select').value !== 'salung') {
        console.error('Test 5 Failed: click row did not set weight/unit', getEl('calc-weight-input').value);
        process.exit(5);
    }
    if (getEl('result-baht').textContent !== '0.250') {
        console.error('Test 5 Failed: 1 salung baht is not 0.250', getEl('result-baht').textContent);
        process.exit(5);
    }

    console.log('ALL NODE CALCULATOR SIMULATION TESTS PASSED');
    """
    test_node_file.write_text(test_node_code, encoding="utf-8")
    try:
        res = subprocess.run(
            ["node", str(test_node_file)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0, f"Node tests failed: {res.stderr} | {res.stdout}"
        assert "ALL NODE CALCULATOR SIMULATION TESTS PASSED" in res.stdout
    finally:
        if test_node_file.exists():
            test_node_file.unlink()
