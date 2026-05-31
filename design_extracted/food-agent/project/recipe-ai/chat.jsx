/* ============================================================
   레시피 AI — Chat view (4단계 인터랙티브 플로우)
   phase: upload → analyzing → servings → extra → generating → review → confirmed
   chatStyle: 'guided'(퀵리플라이 강조) | 'conversational'(자유 입력 강조)
   ============================================================ */
(function () {
  const { Icon, RecipeCard, TypingBubble, parseIng } = window;
  const { useState, useRef, useEffect } = React;
  let _uid = 0;
  const uid = () => 'm' + _uid++;

  function ChatView({ recipeVariant, chatStyle, kitchen, onConfirm, seedRecipe, resetKey }) {
    const [msgs, setMsgs] = useState([]);
    const [phase, setPhase] = useState('upload');
    const [photoPicked, setPhotoPicked] = useState(false);
    const [draft, setDraft] = useState('');
    const [servings, setServings] = useState(2);
    const [recipe, setRecipe] = useState(null);
    const scrollRef = useRef(null);

    // 초기 웰컴 / 리셋
    useEffect(() => {
      setMsgs([{ id: uid(), role: 'ai', type: 'text', content:
        React.createElement('span', null,
          React.createElement('b', null, '안녕하세요, 준규님! '),
          '저는 음식 사진으로 레시피를 만들어 드리는 AI예요. ',
          React.createElement('br'), React.createElement('span', { className: 'sub' },
          '드시고 싶은 음식 사진을 올려주시면 재료를 분석하고 맞춤 레시피를 만들어 드릴게요.')) }]);
      setPhase('upload'); setPhotoPicked(false); setRecipe(null); setServings(2); setDraft('');
    }, [resetKey]);

    // seedRecipe (사이드바/홈에서 레시피 열기)
    useEffect(() => {
      if (!seedRecipe) return;
      setRecipe(seedRecipe); setPhase('review');
      setMsgs([
        { id: uid(), role: 'ai', type: 'text', content: React.createElement('span', null,
          React.createElement(Icon.bookmark, { size: 15, style: { verticalAlign: '-2px', marginRight: 4, color: 'var(--blue)' } }),
          '저장된 ', React.createElement('b', null, seedRecipe.dish_name), ' 레시피를 불러왔어요.') },
        { id: uid(), role: 'ai', type: 'recipe', recipe: seedRecipe },
      ]);
    }, [seedRecipe]);

    useEffect(() => {
      const el = scrollRef.current;
      if (el) requestAnimationFrame(() => { el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }); });
    }, [msgs, phase]);

    const push = (m) => setMsgs((prev) => [...prev, { id: uid(), ...m }]);
    const pushTyping = () => { push({ type: 'typing' }); };
    const dropTyping = () => setMsgs((prev) => prev.filter((m) => m.type !== 'typing'));

    // ── 사진 분석 ──
    function analyze() {
      push({ role: 'user', type: 'photo' });
      setPhase('analyzing');
      pushTyping();
      setTimeout(() => {
        dropTyping();
        const v = window.DATA.demo.vision;
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          React.createElement('b', null, v.dish_name), '으로 분석했어요! 🎉', React.createElement('br'),
          React.createElement('span', { className: 'sub' }, '보이는 재료 — ' + v.ingredients.join(', '))) });
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          '몇 인분으로 만들까요? ', React.createElement('span', { className: 'sub' }, '(기본 2인분)')) });
        setPhase('servings');
      }, 1500);
    }

    // ── 인분 선택 ──
    function chooseServings(n, label) {
      push({ role: 'user', type: 'text', content: label });
      setServings(n);
      pushTyping();
      setTimeout(() => {
        dropTyping();
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          (n ? n + '인분' : '기본 2인분') + '으로 준비할게요 👍', React.createElement('br'),
          React.createElement('span', { className: 'sub' }, '추가 요청사항이 있으신가요? 알러지·못 먹는 재료·난이도 등 — 없으면 건너뛰기')) });
        setPhase('extra');
      }, 900);
    }

    // ── 추가 요청 → 레시피 생성 ──
    function submitExtra(text) {
      if (text) push({ role: 'user', type: 'text', content: text });
      else push({ role: 'user', type: 'text', content: '건너뛰기' });
      setPhase('generating');
      pushTyping();
      setTimeout(() => {
        dropTyping();
        const base = window.DATA.demo.recipe;
        const r = { ...base, servings: servings || 2 };
        setRecipe(r);
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          '레시피가 완성됐어요! 아래에서 확인해 보세요 ✨') });
        push({ role: 'ai', type: 'recipe', recipe: r });
        setPhase('review');
      }, 1700);
    }

    // ── 레시피 확정 ──
    function confirm() {
      push({ role: 'user', type: 'text', content: '레시피 확정!' });
      pushTyping();
      setTimeout(() => {
        dropTyping();
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          React.createElement(Icon.cart, { size: 15, style: { verticalAlign: '-2px', marginRight: 4, color: 'var(--green)' } }),
          '레시피가 저장되고 ', React.createElement('b', null, '장바구니'), '에 추가됐어요!', React.createElement('br'),
          React.createElement('span', { className: 'sub' }, '요리를 마치면 내 주방에서 완료 처리하고 재료를 자동 차감할 수 있어요.')) });
        const missing = (recipe.missing_ingredients || []);
        if (missing.length) {
          push({ role: 'ai', type: 'shopping', missing });
        }
        setPhase('confirmed');
        if (onConfirm) onConfirm(recipe);
      }, 1200);
    }

    // ── 재분석 ──
    function reanalyze() {
      push({ role: 'user', type: 'text', content: '이미지 다시 분석해줘' });
      setPhase('analyzing'); pushTyping();
      setTimeout(() => {
        dropTyping();
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          React.createElement(Icon.refresh, { size: 14, style: { verticalAlign: '-2px', marginRight: 4, color: 'var(--blue)' } }),
          '재분석 완료! 동일하게 ', React.createElement('b', null, '칸놀리'), '로 확인했어요. 같은 설정으로 다시 생성할게요.') });
        setTimeout(() => submitExtraSilent(), 400);
      }, 1400);
    }
    function submitExtraSilent() {
      setPhase('generating'); pushTyping();
      setTimeout(() => {
        dropTyping();
        const r = { ...window.DATA.demo.recipe, servings: servings || 2 };
        setRecipe(r);
        push({ role: 'ai', type: 'recipe', recipe: r });
        setPhase('review');
      }, 1500);
    }

    // ── 수정 요청 ──
    function revise(text) {
      push({ role: 'user', type: 'text', content: text });
      setPhase('generating'); pushTyping();
      setTimeout(() => {
        dropTyping();
        push({ role: 'ai', type: 'text', content: React.createElement('span', null,
          '요청을 반영해 레시피를 다시 다듬었어요 ✏️') });
        const r = { ...window.DATA.demo.recipe, servings: servings || 2 };
        setRecipe(r);
        push({ role: 'ai', type: 'recipe', recipe: r });
        setPhase('review');
      }, 1600);
    }

    // composer 전송
    function sendDraft() {
      const t = draft.trim();
      if (!t) return;
      setDraft('');
      if (phase === 'servings') {
        const m = t.match(/\d+/);
        chooseServings(m ? parseInt(m[0]) : null, t);
      } else if (phase === 'extra') {
        submitExtra(t);
      } else if (phase === 'revising') {
        revise(t);
      }
    }

    const composerActive = ['servings', 'extra', 'revising'].includes(phase);
    const composerPh =
      phase === 'servings' ? '인분 수를 입력하세요 (예: 3인분)'
      : phase === 'extra' ? '요청사항을 입력하세요 (예: 안 맵게 해주세요)'
      : phase === 'revising' ? '어떻게 수정할까요?'
      : '음식 사진을 먼저 올려주세요';

    return React.createElement('div', { className: 'main' },
      // topbar
      React.createElement('div', { className: 'topbar' },
        React.createElement('div', { className: 'msg-ai-avatar', style: { width: 34, height: 34, borderRadius: 10 } },
          React.createElement(Icon.chef, { size: 17 })),
        React.createElement('div', null,
          React.createElement('div', { className: 'topbar-title' }, '레시피 AI'),
          React.createElement('div', { className: 'topbar-sub' }, '음식 사진 → 맞춤 레시피')),
        React.createElement('div', { className: 'topbar-spacer' }),
        React.createElement('div', { className: 'topbar-status' },
          React.createElement('span', { className: 'live-dot' }), '항상 활성화')
      ),

      // messages
      React.createElement('div', { className: 'scroll', ref: scrollRef },
        React.createElement('div', { className: 'chat-wrap' },
          React.createElement('div', { className: 'day-sep' }, React.createElement('span', null, '오늘 · 음식 사진 레시피')),
          msgs.map((m) => renderMsg(m, recipeVariant, kitchen)),

          // upload zone
          phase === 'upload' ? React.createElement(UploadZone, {
            picked: photoPicked,
            onPick: () => setPhotoPicked(true),
            onAnalyze: analyze,
          }) : null,

          // quick replies — guided: 즉시 전송 / conversational: 입력창 채우기
          phase === 'servings' ? (chatStyle === 'conversational'
            ? React.createElement('div', { className: 'suggest-row fade-up' },
                React.createElement('span', { className: 'suggest-label' }, '추천'),
                ['1인분', '2인분', '4인분', '6인분'].map((l) =>
                  React.createElement('button', { key: l, className: 'suggest-chip', onClick: () => { setDraft(l); } }, l)),
                React.createElement('button', { className: 'suggest-chip', onClick: () => chooseServings(null, '건너뛰기') }, '건너뛰기'))
            : React.createElement('div', { className: 'quick-row fade-up' },
                [['1인분', 1], ['2인분', 2], ['4인분', 4], ['6인분', 6]].map(([l, n]) =>
                  React.createElement('button', { key: n, className: 'chip', onClick: () => chooseServings(n, l) }, l)),
                React.createElement('button', { className: 'chip', onClick: () => chooseServings(null, '건너뛰기') }, '건너뛰기 →'))
          ) : null,

          phase === 'extra' ? (chatStyle === 'conversational'
            ? React.createElement('div', { className: 'suggest-row fade-up' },
                React.createElement('span', { className: 'suggest-label' }, '추천'),
                ['채식으로 바꿔줘', '안 맵게', '10분 이내', '설탕 줄여줘'].map((l) =>
                  React.createElement('button', { key: l, className: 'suggest-chip', onClick: () => { setDraft(l); } },
                    React.createElement(Icon.sparkle2, { size: 13 }), l)),
                React.createElement('button', { className: 'suggest-chip', onClick: () => submitExtra('') }, '건너뛰기'))
            : React.createElement('div', { className: 'quick-row fade-up' },
                ['채식으로 바꿔줘', '안 맵게', '10분 이내', '설탕 줄여줘'].map((l) =>
                  React.createElement('button', { key: l, className: 'chip', onClick: () => submitExtra(l) },
                    React.createElement(Icon.sparkle2, { size: 14 }), l)),
                React.createElement('button', { className: 'chip', onClick: () => submitExtra('') }, '건너뛰기 →'))
          ) : null,

          // review actions
          phase === 'review' ? React.createElement('div', { className: 'quick-row fade-up', style: { marginLeft: 0 } },
            React.createElement('button', { className: 'btn btn-primary', onClick: confirm },
              React.createElement(Icon.check, { size: 17 }), '레시피 확정'),
            React.createElement('button', { className: 'btn btn-ghost', onClick: () => { push({ role: 'user', type: 'text', content: '수정 요청' }); push({ role: 'ai', type: 'text', content: React.createElement('span', null, '어떻게 수정할까요? ', React.createElement('span', { className: 'sub' }, '예: 채식으로, 난이도 낮춰줘, 10분 이내')) }); setPhase('revising'); } },
              React.createElement(Icon.edit, { size: 16 }), '수정 요청'),
            React.createElement('button', { className: 'btn btn-ghost', onClick: reanalyze },
              React.createElement(Icon.refresh, { size: 16 }), '이미지 재분석')
          ) : null,

          phase === 'confirmed' ? React.createElement('div', { className: 'quick-row fade-up', style: { marginLeft: 0 } },
            React.createElement('button', { className: 'btn btn-soft', onClick: () => window.dispatchEvent(new CustomEvent('go-kitchen')) },
              React.createElement(Icon.fridge, { size: 16 }), '내 주방에서 완료 처리'),
            React.createElement('button', { className: 'btn btn-ghost', onClick: () => window.dispatchEvent(new CustomEvent('new-chat')) },
              React.createElement(Icon.refresh, { size: 16 }), '처음부터 다시')
          ) : null,
        )
      ),

      // composer
      React.createElement('div', { className: 'composer-wrap' },
        React.createElement('div', { className: 'composer' },
          React.createElement('button', { className: 'composer-icon-btn', title: '사진 첨부',
            onClick: () => { if (phase === 'upload') setPhotoPicked(true); } },
            React.createElement(Icon.image, { size: 20 })),
          React.createElement('div', { className: 'composer-box' },
            React.createElement('input', {
              className: 'composer-input', placeholder: composerPh, value: draft,
              disabled: !composerActive,
              onChange: (e) => setDraft(e.target.value),
              onKeyDown: (e) => { if (e.key === 'Enter') sendDraft(); },
            }),
            React.createElement('button', { className: 'composer-send', disabled: !composerActive || !draft.trim(), onClick: sendDraft },
              React.createElement(Icon.send, { size: 18 }))
          )
        )
      )
    );
  }

  // ── 메시지 렌더 ──
  function renderMsg(m, recipeVariant, kitchen) {
    if (m.type === 'typing') return React.createElement(TypingBubble, { key: m.id });
    if (m.role === 'user') {
      if (m.type === 'photo')
        return React.createElement('div', { className: 'msg-user fade-up', key: m.id },
          React.createElement('div', { className: 'bubble-user photo' },
            React.createElement('div', { className: 'ph food', style: { width: 220, height: 165, background: window.DATA.demo.recipe.hero } },
              React.createElement('span', null, '내가 올린 음식 사진'))));
      return React.createElement('div', { className: 'msg-user fade-up', key: m.id },
        React.createElement('div', { className: 'bubble-user' }, m.content));
    }
    // AI
    if (m.type === 'recipe')
      return React.createElement('div', { className: 'msg-ai fade-up', key: m.id, style: { maxWidth: '94%' } },
        React.createElement('div', { className: 'msg-ai-avatar' }, React.createElement(Icon.chef, { size: 18 })),
        React.createElement('div', { style: { flex: 1, minWidth: 0 } },
          React.createElement(RecipeCard, { recipe: m.recipe, variant: recipeVariant, kitchen, showHero: recipeVariant === 'magazine' })));
    if (m.type === 'shopping')
      return React.createElement('div', { className: 'msg-ai fade-up', key: m.id, style: { maxWidth: '90%' } },
        React.createElement('div', { className: 'msg-ai-avatar' }, React.createElement(Icon.chef, { size: 18 })),
        React.createElement('div', { className: 'bubble-ai', style: { flex: 1 } },
          React.createElement('b', null, '🛒 필요한 재료 바로 구매하기'),
          m.missing.map((mi) => React.createElement(ShoppingGroup, { key: mi, ingName: parseIng(mi).name }))));
    return React.createElement('div', { className: 'msg-ai fade-up', key: m.id },
      React.createElement('div', { className: 'msg-ai-avatar' }, React.createElement(Icon.chef, { size: 18 })),
      React.createElement('div', { className: 'bubble-ai' }, m.content));
  }

  function ShoppingGroup({ ingName }) {
    const items = window.DATA.shoppingEgg;
    return React.createElement('div', { className: 'shop-block' },
      React.createElement('div', { className: 'shop-ing-label' },
        React.createElement('span', { className: 'tag tag-amber' }, '구매 필요'), ingName),
      items.map((it, i) =>
        React.createElement('a', { key: i, className: 'shop-item', href: '#', onClick: (e) => e.preventDefault() },
          React.createElement('div', { className: 'shop-thumb ph', style: { background: it.tone } }),
          React.createElement('div', { style: { minWidth: 0, flex: 1 } },
            React.createElement('div', { className: 'shop-mall' }, it.mall),
            React.createElement('div', { className: 'shop-title' }, it.title)),
          React.createElement('div', { className: 'shop-price' }, '₩' + it.price.toLocaleString())))
    );
  }

  function UploadZone({ picked, onPick, onAnalyze }) {
    return React.createElement('div', { style: { marginLeft: 48, maxWidth: 420, marginBottom: 18 } },
      !picked
        ? React.createElement('div', { className: 'upload-zone fade-up', onClick: onPick },
            React.createElement('div', { className: 'upload-ic' }, React.createElement(Icon.upload, { size: 24 })),
            React.createElement('h4', null, '음식 사진 올리기'),
            React.createElement('p', null, '클릭해서 사진을 선택하세요 · JPG·PNG·WEBP · 4MB 이하'))
        : React.createElement('div', { className: 'fade-up' },
            React.createElement('div', { className: 'ph food', style: { height: 175, borderRadius: 'var(--r-lg)', background: window.DATA.demo.recipe.hero, marginBottom: 12, border: '1px solid var(--line)' } },
              React.createElement('span', null, 'IMG_2048.jpg · 칸놀리')),
            React.createElement('div', { style: { display: 'flex', gap: 9 } },
              React.createElement('button', { className: 'btn btn-primary btn-lg', style: { flex: 1 }, onClick: onAnalyze },
                React.createElement(Icon.camera, { size: 18 }), '사진 분석하기'),
              React.createElement('button', { className: 'btn btn-ghost btn-lg', onClick: onPick, title: '다시 선택' },
                React.createElement(Icon.refresh, { size: 17 })))));
  }

  window.ChatView = ChatView;
})();
