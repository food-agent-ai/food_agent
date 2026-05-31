/* ============================================================
   레시피 AI — Completion (재료 차감 계산 + 완료 처리 모달)
   main.py calculate_source_update 로직 미러링
   ============================================================ */
(function () {
  const { Icon, parseIng } = window;

  const UNIT_CONV = { kg: ['g', 1000], L: ['ml', 1000] };
  const AMT_RE = /^(\d+(?:\.\d+)?)(g|kg|ml|L|개|알|큰술|작은술|컵|줄기|묶음|장|쪽|톨|팩|봉|캔)$/;

  function parseAmt(s) {
    const m = String(s || '').trim().match(AMT_RE);
    if (!m) return null;
    let q = parseFloat(m[1]); let u = m[2];
    if (UNIT_CONV[u]) { q *= UNIT_CONV[u][1]; u = UNIT_CONV[u][0]; }
    return [q, u];
  }
  const fmtAmt = (q, u) => (Number.isInteger(q) ? q : q) + u;

  // 차감 계산
  function calcCompletion(recipe, kitchen) {
    const byName = {};
    kitchen.ingredients.forEach((i) => (byName[i.name] = { ...i }));
    const missingNames = new Set((recipe.missing_ingredients || []).map((m) => parseIng(m).name));
    const all = (recipe.ingredients || []).map(parseIng);
    const used = [], blocked = [], missing = [];
    (recipe.missing_ingredients || []).forEach((m) => missing.push(parseIng(m)));

    all.forEach((ing) => {
      if (missingNames.has(ing.name)) return;
      const src = byName[ing.name];
      if (!src) { blocked.push({ ...ing, reason: '주방에 없는 재료' }); return; }
      const cur = src.amount.trim();
      if (!cur) { blocked.push({ ...ing, reason: '보유량 정보 없음' }); return; }
      const c = parseAmt(cur), r = parseAmt(ing.amount);
      if (!r) { blocked.push({ ...ing, reason: '필요량 단위 미지원' }); return; }
      if (!c) { blocked.push({ ...ing, reason: '보유량 단위 미지원' }); return; }
      if (c[1] !== r[1]) { blocked.push({ ...ing, reason: `단위 다름 (보유 ${c[1]}, 필요 ${r[1]})` }); return; }
      if (c[0] < r[0]) { blocked.push({ ...ing, reason: `보유량 부족 (보유 ${cur})` }); return; }
      const after = c[0] - r[0];
      used.push({ name: ing.name, amount: ing.amount, before: cur, after: after === 0 ? '소진' : fmtAmt(after, c[1]) });
      byName[ing.name].amount = fmtAmt(after, c[1]);
    });
    const updated = kitchen.ingredients
      .map((i) => byName[i.name] || i)
      .filter((i) => { const p = parseAmt(i.amount); return !(p && p[0] === 0); });
    return { used, blocked, missing, updatedIngredients: updated };
  }

  // 완료 처리 모달
  function CompletionModal({ recipe, kitchen, onClose, onComplete }) {
    const res = calcCompletion(recipe, kitchen);
    return React.createElement('div', { className: 'modal-overlay', onClick: onClose },
      React.createElement('div', { className: 'modal fade-up', onClick: (e) => e.stopPropagation() },
        React.createElement('div', { className: 'modal-head' },
          React.createElement('div', { className: 'sb-recipe-thumb', style: { width: 38, height: 38, fontSize: 19 } }, recipe.emoji),
          React.createElement('div', { style: { flex: 1 } },
            React.createElement('div', { style: { fontWeight: 800, fontSize: 16 } }, recipe.dish_name + ' 완료 처리'),
            React.createElement('div', { style: { fontSize: 12.5, color: 'var(--ink-3)' } }, '사용한 재료를 주방에서 자동 차감해요')),
          React.createElement('button', { className: 'modal-x', onClick: onClose }, React.createElement(Icon.x, { size: 18 }))),
        React.createElement('div', { className: 'modal-body' },
          res.used.length ? React.createElement('div', { className: 'comp-group' },
            React.createElement('div', { className: 'comp-label' },
              React.createElement(Icon.checkCircle, { size: 15, style: { color: 'var(--green)' } }), '자동 차감'),
            res.used.map((u, i) => React.createElement('div', { className: 'complete-line', key: i },
              React.createElement('span', { className: 'cl-ic', style: { background: 'var(--green-soft)', color: 'var(--green-ink)' } },
                React.createElement(Icon.check, { size: 13, sw: 2.4 })),
              React.createElement('span', { className: 'nm' }, u.name),
              React.createElement('span', { className: 'mono', style: { fontSize: 12, color: 'var(--ink-3)' } }, u.amount),
              React.createElement('span', { className: 'chg' }, u.before, ' → ', React.createElement('b', null, u.after))))) : null,
          res.blocked.length ? React.createElement('div', { className: 'comp-group' },
            React.createElement('div', { className: 'comp-label' },
              React.createElement(Icon.ban, { size: 15, style: { color: 'var(--amber)' } }), '수동 확인 필요'),
            res.blocked.map((b, i) => React.createElement('div', { className: 'complete-line', key: i },
              React.createElement('span', { className: 'cl-ic', style: { background: 'var(--amber-soft)', color: 'var(--amber-ink)' } },
                React.createElement(Icon.sliders, { size: 13 })),
              React.createElement('span', { className: 'nm' }, b.name),
              React.createElement('span', { className: 'chg', style: { color: 'var(--ink-3)' } }, b.reason)))) : null,
          res.missing.length ? React.createElement('div', { className: 'comp-group' },
            React.createElement('div', { className: 'comp-label' },
              React.createElement(Icon.cart, { size: 15, style: { color: 'var(--blue)' } }), '추가 준비 필요'),
            res.missing.map((m, i) => React.createElement('div', { className: 'complete-line', key: i },
              React.createElement('span', { className: 'cl-ic', style: { background: 'var(--blue-soft)', color: 'var(--blue-ink)' } },
                React.createElement(Icon.plus, { size: 13 })),
              React.createElement('span', { className: 'nm' }, m.name),
              React.createElement('span', { className: 'chg', style: { color: 'var(--ink-3)' } }, m.amount || '수량 미정')))) : null
        ),
        React.createElement('div', { className: 'modal-foot' },
          React.createElement('button', { className: 'btn btn-ghost', onClick: onClose }, '취소'),
          React.createElement('button', { className: 'btn btn-green', onClick: () => onComplete(recipe, res) },
            React.createElement(Icon.check, { size: 17 }), '완료 확정 · 재료 차감'))
      )
    );
  }

  window.calcCompletion = calcCompletion;
  window.CompletionModal = CompletionModal;
})();
