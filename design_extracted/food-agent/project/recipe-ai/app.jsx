/* ============================================================
   레시피 AI — App (라우팅 + 상태 + Tweaks)
   ============================================================ */
(function () {
  const { Icon, Sidebar, HomeBoard, ChatView, KitchenView, CompletionModal } = window;
  const { useState, useEffect, useRef } = React;
  const {
    useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakColor,
  } = window;

  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "accent": "#2F6BFF",
    "recipeVariant": "classic",
    "chatStyle": "guided",
    "homeLayout": "grid"
  }/*EDITMODE-END*/;

  const ACCENTS = {
    '#2F6BFF': { name: '클래식 블루', soft: '#ECF1FF', soft2: '#E0E8FF', ink: '#1B47B8', d600: '#1F5BF0', d700: '#1A4FD6', blue700b: '#1A4FD6' },
    '#0E9E83': { name: '쿠킹 틸', soft: '#E1F5F0', soft2: '#CDEDE5', ink: '#0A6E5C', d600: '#0C8D75', d700: '#0A7763' },
    '#E0662B': { name: '웜 테라코타', soft: '#FBEDE3', soft2: '#F6DDCB', ink: '#A8481B', d600: '#CF5A22', d700: '#B44E1D' },
  };

  function applyAccent(hex) {
    const a = ACCENTS[hex] || ACCENTS['#2F6BFF'];
    const r = document.documentElement.style;
    r.setProperty('--blue', hex);
    r.setProperty('--blue-600', a.d600);
    r.setProperty('--blue-700', a.d700);
    r.setProperty('--blue-soft', a.soft);
    r.setProperty('--blue-soft-2', a.soft2);
    r.setProperty('--blue-ink', a.ink);
    // shadow tint
    const rgb = hex.match(/\w\w/g).map((x) => parseInt(x, 16)).join(',');
    r.setProperty('--sh-blue', `0 6px 18px rgba(${rgb},.28)`);
  }

  function App() {
    const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
    const [view, setView] = useState('home');
    const [recipes, setRecipes] = useState(() => window.DATA.recipes.map((r) => ({ ...r })));
    const [kitchen, setKitchen] = useState(() => ({
      ...window.DATA.kitchen,
      ingredients: window.DATA.kitchen.ingredients.map((i) => ({ ...i })),
      preferences: window.DATA.kitchen.preferences.map((p) => ({ ...p })),
    }));
    const [seedRecipe, setSeedRecipe] = useState(null);
    const [resetKey, setResetKey] = useState(0);
    const [activeRecipeId, setActiveRecipeId] = useState(null);
    const [completeTarget, setCompleteTarget] = useState(null);
    const [toast, setToast] = useState(null);

    useEffect(() => { applyAccent(t.accent); }, [t.accent]);

    // 글로벌 이벤트 (chat → 다른 뷰 이동)
    useEffect(() => {
      const goKitchen = () => setView('kitchen');
      const newChat = () => startNewChat();
      window.addEventListener('go-kitchen', goKitchen);
      window.addEventListener('new-chat', newChat);
      return () => { window.removeEventListener('go-kitchen', goKitchen); window.removeEventListener('new-chat', newChat); };
    });

    function startNewChat() {
      setSeedRecipe(null); setActiveRecipeId(null);
      setResetKey((k) => k + 1); setView('chat');
    }
    function openRecipe(r) {
      setSeedRecipe(r); setActiveRecipeId(r.id); setView('chat');
    }
    function onConfirm(recipe) {
      // 채팅에서 확정된 데모 레시피를 장바구니에 추가 (중복 방지)
      setRecipes((prev) => prev.some((p) => p.id === recipe.id) ? prev
        : [{ ...recipe, kind: 'cart', saved_at: '방금 전' }, ...prev]);
    }
    function doComplete(recipe, res) {
      setKitchen((prev) => ({ ...prev, ingredients: res.updatedIngredients, updated: '2026-05-31' }));
      setRecipes((prev) => prev.map((r) => r.id === recipe.id
        ? { ...r, kind: 'library', completed_at: '2026-05-31', saved_at: r.saved_at } : r));
      setCompleteTarget(null);
      showToast(recipe.dish_name + ' 완료! 재료 ' + res.used.length + '종이 주방에서 차감됐어요.');
    }
    function showToast(msg) {
      setToast(msg);
      setTimeout(() => setToast(null), 3200);
    }

    let content;
    if (view === 'home')
      content = React.createElement('div', { className: 'main' },
        React.createElement('div', { className: 'topbar' },
          React.createElement('div', { className: 'topbar-title' }, '홈'),
          React.createElement('div', { className: 'topbar-sub', style: { marginLeft: 2 } }, '· 레시피 대시보드'),
          React.createElement('div', { className: 'topbar-spacer' }),
          React.createElement('button', { className: 'btn btn-primary btn-sm', onClick: startNewChat },
            React.createElement(Icon.camera, { size: 16 }), '새 레시피')),
        React.createElement(HomeBoard, { recipes, kitchen, layout: t.homeLayout, onNewChat: startNewChat, onOpenRecipe: openRecipe, setView }));
    else if (view === 'chat')
      content = React.createElement(ChatView, {
        key: 'chat', recipeVariant: t.recipeVariant, chatStyle: t.chatStyle,
        kitchen, onConfirm, seedRecipe, resetKey });
    else if (view === 'kitchen')
      content = React.createElement(KitchenView, { kitchen, setKitchen, recipes, onComplete: setCompleteTarget });

    return React.createElement('div', { className: 'app' },
      React.createElement(Sidebar, { view, setView, recipes, onNewChat: startNewChat, onOpenRecipe: openRecipe, activeRecipeId }),
      content,
      completeTarget ? React.createElement(CompletionModal, {
        recipe: completeTarget, kitchen, onClose: () => setCompleteTarget(null), onComplete: doComplete }) : null,
      toast ? React.createElement('div', { className: 'toast fade-up' },
        React.createElement(Icon.checkCircle, { size: 18, style: { color: 'var(--green)' } }), toast) : null,

      // ── Tweaks ──
      React.createElement(TweaksPanel, { title: 'Tweaks' },
        React.createElement(TweakSection, { label: '비주얼' }),
        React.createElement(TweakColor, { label: '액센트 컬러', value: t.accent,
          options: ['#2F6BFF', '#0E9E83', '#E0662B'],
          onChange: (v) => setTweak('accent', v) }),
        React.createElement(TweakSection, { label: '레시피 카드 레이아웃' }),
        React.createElement(TweakRadio, { label: '스타일', value: t.recipeVariant,
          options: ['classic', 'magazine', 'compact'],
          onChange: (v) => setTweak('recipeVariant', v) }),
        React.createElement('div', { style: { fontSize: 11.5, color: 'var(--ink-3, #8A93A3)', padding: '2px 2px 8px', lineHeight: 1.5 } },
          'classic 세로형 · magazine 상단 사진 · compact 체크리스트'),
        React.createElement(TweakSection, { label: '채팅 인터랙션' }),
        React.createElement(TweakRadio, { label: '방식', value: t.chatStyle,
          options: ['guided', 'conversational'],
          onChange: (v) => setTweak('chatStyle', v) }),
        React.createElement(TweakSection, { label: '홈 보드' }),
        React.createElement(TweakRadio, { label: '이전 레시피', value: t.homeLayout,
          options: ['grid', 'list'],
          onChange: (v) => setTweak('homeLayout', v) }),
      )
    );
  }

  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
})();
