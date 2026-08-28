import { useEffect, useMemo, useState } from 'react';

const heroOutcomes = ['conformidade.', 'produtividade.', 'confiança.'];
const contactPhone = import.meta.env.VITE_PONTIX_WHATSAPP_NUMBER ?? '5518988085156';
const contactEmail = import.meta.env.VITE_PONTIX_CONTACT_EMAIL ?? 'grbtecnologia.cm@gmail.com';

const contactMessage = encodeURIComponent('Olá! Quero uma demonstração do Pontix.');
const emailSubject = encodeURIComponent('Demonstração do Pontix');
const emailBody = encodeURIComponent(
  'Olá! Gostaria de receber uma demonstração do Pontix e entender como ele pode ajudar na gestão de ponto da minha operação.'
);

const whatsappLink = `https://wa.me/${contactPhone.replace(/\D/g, '')}?text=${contactMessage}`;
const emailLink = `mailto:${contactEmail}?subject=${emailSubject}&body=${emailBody}`;

const features = [
  {
    title: 'Ponto facial com prova de vida',
    text: 'Registro pensado para reduzir fraude, evitar marcação por terceiros e deixar a jornada mais confiável desde a entrada.',
    icon: 'face',
  },
  {
    title: 'Painel operacional em tempo real',
    text: 'Acompanhe presentes, atrasos, movimentos e status da operação sem depender de planilhas espalhadas.',
    icon: 'pulse',
  },
  {
    title: 'Relatórios e espelho de ponto',
    text: 'Fechamento mais rápido com histórico local, exportação organizada e apoio à conferência diária.',
    icon: 'report',
  },
  {
    title: 'Auditoria e trilha de ações',
    text: 'Toda alteração fica rastreável para dar segurança ao time de RH e reduzir risco na fiscalização.',
    icon: 'shield',
  },
];

const milestones = [
  {
    step: '01',
    title: 'Captura',
    text: 'O colaborador registra entrada, saída ou intervalo com leitura confiável e contexto da unidade.',
  },
  {
    step: '02',
    title: 'Validação',
    text: 'O sistema consolida o evento, identifica inconsistências e organiza a jornada em tempo real.',
  },
  {
    step: '03',
    title: 'Fechamento',
    text: 'RH e operação enxergam dados prontos para conferência, relatórios e auditoria.',
  },
];

const recentEvents = [
  ['Ana Martins', 'Entrada', '08:02', 'Matriz'],
  ['Rafael Costa', 'Intervalo', '12:01', 'Unidade Norte'],
  ['Luiza Melo', 'Saída', '18:04', 'Centro de Operações'],
  ['Carlos Eduardo', 'Entrada', '07:58', 'Matriz'],
];

function Icon({ name }) {
  if (name === 'face') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm-3 8.2a1.2 1.2 0 1 1 1.2-1.2A1.2 1.2 0 0 1 9 10.2Zm6 0a1.2 1.2 0 1 1 1.2-1.2A1.2 1.2 0 0 1 15 10.2Zm-6.8 4.1a.8.8 0 0 1 1.1-.2 4.5 4.5 0 0 0 5.6 0 .8.8 0 1 1 .9 1.3 6.1 6.1 0 0 1-7.6 0 .8.8 0 0 1-.2-1.1Z" />
      </svg>
    );
  }

  if (name === 'report') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 2h8l4 4v16H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm7 1.5V7h3.5Z" />
        <path d="M8 11h8M8 14h8M8 17h6" />
      </svg>
    );
  }

  if (name === 'shield') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 2 8 4v6c0 5.1-3.4 8.6-8 10-4.6-1.4-8-4.9-8-10V6l8-4Z" />
        <path d="m9.2 12.2 1.9 1.9 3.7-3.7" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v3M12 18v3M4.2 12H1.2M22.8 12h-3M5.5 5.5 3.6 3.6M20.4 20.4l-1.9-1.9M18.5 5.5l1.9-1.9M3.6 20.4l1.9-1.9" />
      <circle cx="12" cy="12" r="5.5" />
    </svg>
  );
}

function App() {
  const [rotIndex, setRotIndex] = useState(0);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const rotate = window.setInterval(() => {
      setRotIndex((current) => (current + 1) % heroOutcomes.length);
    }, 2600);

    const clock = window.setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => {
      window.clearInterval(rotate);
      window.clearInterval(clock);
    };
  }, []);

  const formattedClock = useMemo(
    () =>
      new Intl.DateTimeFormat('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(now),
    [now]
  );

  const formattedDate = useMemo(
    () =>
      new Intl.DateTimeFormat('pt-BR', {
        weekday: 'short',
        day: '2-digit',
        month: 'short',
      }).format(now),
    [now]
  );

  return (
    <div className="page-shell">
      <div className="bg-grid" />
      <div className="bg-orb bg-orb-a" />
      <div className="bg-orb bg-orb-b" />

      <header className="topbar">
        <div className="container topbar-inner">
          <a className="brand" href="#inicio">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
            </span>
            <span>
              Pontix
              <small>GRB Tecnologia</small>
            </span>
          </a>

          <nav className="nav">
            <a href="#produto">Produto</a>
            <a href="#fluxo">Fluxo</a>
            <a href={whatsappLink} target="_blank" rel="noreferrer" className="nav-cta">
              Solicitar demonstração
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section id="inicio" className="hero section">
          <div className="container hero-grid">
            <div className="hero-copy">
              <span className="eyebrow">
                <span className="eyebrow-dot" />
                Tempo preciso. Decisões seguras.
              </span>
              <h1>
                Cada marcação vira <span key={rotIndex}>{heroOutcomes[rotIndex]}</span>
              </h1>
              <p className="lead">
                O Pontix organiza a gestão de ponto do início ao fim com marcação facial,
                conferência operacional, relatórios e auditoria. Um sistema criado para a rotina
                de empresas que precisam de clareza, rastreabilidade e menos retrabalho.
              </p>

              <div className="hero-actions">
                <a href={whatsappLink} target="_blank" rel="noreferrer" className="btn btn-primary">
                  Solicitar demonstração
                  <span aria-hidden="true">↗</span>
                </a>
                <a href={emailLink} className="btn btn-ghost">
                  Falar por e-mail
                </a>
              </div>

              <div className="proof-row">
                <div>
                  <strong>99,9%</strong>
                  <span>disponibilidade planejada</span>
                </div>
                <div>
                  <strong>LGPD</strong>
                  <span>proteção por design</span>
                </div>
                <div>
                  <strong>Portaria 671</strong>
                  <span>fluxo compatível</span>
                </div>
              </div>
            </div>

            <aside className="hero-card" aria-label="Painel ao vivo">
              <div className="hero-card-top">
                <span>{formattedDate.toUpperCase()}</span>
                <span className="live-badge">
                  <i />
                  ao vivo
                </span>
              </div>

              <div className="clock-panel">
                <div className="clock-digit">{formattedClock.slice(0, 2)}</div>
                <div className="clock-sep">:</div>
                <div className="clock-digit">{formattedClock.slice(3, 5)}</div>
                <div className="clock-sep">:</div>
                <div className="clock-digit">{formattedClock.slice(6, 8)}</div>
              </div>

              <div className="hero-card-note">
                Câmera facial ativa · Portaria principal · Unidade Matriz
              </div>

              <div className="hero-metrics">
                <div>
                  <span>Presentes hoje</span>
                  <strong>238 / 248</strong>
                </div>
                <div>
                  <span>Horas registradas</span>
                  <strong>1.904h</strong>
                </div>
                <div>
                  <span>Eventos validados</span>
                  <strong>100%</strong>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section id="produto" className="section section-surface">
          <div className="container">
            <div className="section-heading">
              <span className="section-tag">O SISTEMA EM UMA VISÃO</span>
              <h2>Uma landing que vende o produto com a mesma clareza do painel interno.</h2>
              <p>
                A proposta do Pontix é tirar o peso operacional do controle de jornada e colocar
                o foco no que importa: marcação confiável, conferência rápida e evidência pronta
                para o RH.
              </p>
            </div>

            <div className="feature-grid">
              {features.map((feature) => (
                <article className="feature-card" key={feature.title}>
                  <div className="feature-icon">
                    <Icon name={feature.icon} />
                  </div>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="fluxo" className="section">
          <div className="container workflow-grid">
            <div className="workflow-copy">
              <span className="section-tag">COMO FUNCIONA</span>
              <h2>Do registro até o fechamento, o fluxo fica simples para quem opera e confiável para quem audita.</h2>
              <p>
                A landing também precisa comunicar maturidade do sistema. Por isso, o texto deixa
                claro que o Pontix não é só ponto facial: ele conecta o registro ao acompanhamento
                da jornada, relatórios e trilha de auditoria.
              </p>
            </div>

            <div className="timeline">
              {milestones.map((item) => (
                <article className="timeline-item" key={item.title}>
                  <span className="timeline-step">{item.step}</span>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section section-surface">
          <div className="container operations-grid">
            <article className="operations-card">
              <div className="section-heading compact">
                <span className="section-tag">ATIVIDADE RECENTE</span>
                <h2>Últimas marcações com leitura clara e pronta para conferência.</h2>
              </div>
              <div className="event-list">
                {recentEvents.map(([name, action, time, location]) => (
                  <div className="event-row" key={`${name}-${time}`}>
                    <div>
                      <strong>{name}</strong>
                      <span>{location}</span>
                    </div>
                    <div>
                      <span className="event-action">{action}</span>
                      <strong>{time}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article className="operations-card">
              <div className="section-heading compact">
                <span className="section-tag">DIFERENCIAIS</span>
                <h2>O que a empresa ganha com o Pontix.</h2>
              </div>
              <div className="benefit-list">
                <div>
                  <strong>Menos retrabalho</strong>
                  <p>Dados organizados para evitar planilhas paralelas e conferência manual demorada.</p>
                </div>
                <div>
                  <strong>Mais rastreabilidade</strong>
                  <p>Histórico e auditoria ajudam na tomada de decisão e reduzem ruído entre áreas.</p>
                </div>
                <div>
                  <strong>Melhor apresentação</strong>
                  <p>Uma landing premium transmite confiança antes mesmo da primeira demonstração.</p>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section id="contato" className="section contact-section">
          <div className="container contact-card">
            <div className="contact-copy">
              <span className="section-tag">PRONTO PARA DEMONSTRAR</span>
              <h2>Vamos mostrar o Pontix com a cara do seu negócio.</h2>
              <p>
                A estrutura foi pensada para funcionar bem no Vercel com React e apresentar o
                sistema de forma mais bonita, moderna e alinhada ao que vocês já construíram.
              </p>
              <div className="contact-points">
                <span>Sem instalação complexa</span>
                <span>Layout responsivo</span>
                <span>Deploy fácil na Vercel</span>
              </div>
            </div>

            <div className="contact-form">
              <a href={whatsappLink} target="_blank" rel="noreferrer" className="btn btn-primary btn-full">
                Falar no WhatsApp
                <span aria-hidden="true">↗</span>
              </a>
              <a href={emailLink} className="btn btn-ghost btn-full">
                Enviar e-mail
              </a>
              <p className="form-note">Resposta em até 1 dia útil · Pontix</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <a className="brand footer-brand" href="#inicio">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
            </span>
            <span>
              Pontix
              <small>GRB Tecnologia</small>
            </span>
          </a>

          <div className="footer-links">
            <a href="#produto">Produto</a>
            <a href="#fluxo">Fluxo</a>
            <a href="#contato">Contato</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
