'use client';

/* ─── Brand SVG Icons ────────────────────────────────────
 *  Single source of truth for all model/provider icons.
 *  Replace these SVGs with your official brand assets.
 *  Each icon: 16x16 default, accepts className + size props.
 * ────────────────────────────────────────────────────────── */

interface IconProps {
  className?: string;
  size?: number;
}

export function KraitIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      {/* Sinuous snake body */}
      <path
        d="M4 12c0-2.7 2-4.7 4-4.7s4 2 4 4.7-2 4.7-4 4.7c-1.3 0-2-.7-2-2 0-1.3 1.3-2 2.7-2s2.7.7 2.7 2"
        stroke="#FACC15"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      {/* Tail tuck */}
      <path
        d="M14.7 13.3c1.3-.7 3.3-.3 4.7 1"
        stroke="#FACC15"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      {/* Head */}
      <circle cx="4.7" cy="12" r="1.6" fill="#FACC15" />
      {/* Antenna / highlight */}
      <line x1="4.7" y1="10" x2="6.4" y2="8.3" stroke="#FACC15" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function ClaudeIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="#D97757" className={className}>
      <path d="m19.6 66.5 19.7-11 .3-1-.3-.5h-1l-3.3-.2-11.2-.3L14 53l-9.5-.5-2.4-.5L0 49l.2-1.5 2-1.3 2.9.2 6.3.5 9.5.6 6.9.4L38 49.1h1.6l.2-.7-.5-.4-.4-.4L29 41l-10.6-7-5.6-4.1-3-2-1.5-2-.6-4.2 2.7-3 3.7.3.9.2 3.7 2.9 8 6.1L37 36l1.5 1.2.6-.4.1-.3-.7-1.1L33 25l-6-10.4-2.7-4.3-.7-2.6c-.3-1-.4-2-.4-3l3-4.2L28 0l4.2.6L33.8 2l2.6 6 4.1 9.3L47 29.9l2 3.8 1 3.4.3 1h.7v-.5l.5-7.2 1-8.7 1-11.2.3-3.2 1.6-3.8 3-2L61 2.6l2 2.9-.3 1.8-1.1 7.7L59 27.1l-1.5 8.2h.9l1-1.1 4.1-5.4 6.9-8.6 3-3.5L77 13l2.3-1.8h4.3l3.1 4.7-1.4 4.9-4.4 5.6-3.7 4.7-5.3 7.1-3.2 5.7.3.4h.7l12-2.6 6.4-1.1 7.6-1.3 3.5 1.6.4 1.6-1.4 3.4-8.2 2-9.6 2-14.3 3.3-.2.1.2.3 6.4.6 2.8.2h6.8l12.6 1 3.3 2 1.9 2.7-.3 2-5.1 2.6-6.8-1.6-16-3.8-5.4-1.3h-.8v.4l4.6 4.5 8.3 7.5L89 80.1l.5 2.4-1.3 2-1.4-.2-9.2-7-3.6-3-8-6.8h-.5v.7l1.8 2.7 9.8 14.7.5 4.5-.7 1.4-2.6 1-2.7-.6-5.8-8-6-9-4.7-8.2-.5.4-2.9 30.2-1.3 1.5-3 1.2-2.5-2-1.4-3 1.4-6.2 1.6-8 1.3-6.4 1.2-7.9.7-2.6v-.2H49L43 72l-9 12.3-7.2 7.6-1.7.7-3-1.5.3-2.8L24 86l10-12.8 6-7.9 4-4.6-.1-.5h-.3L17.2 77.4l-4.7.6-2-2 .2-3 1-1 8-5.5Z" />
    </svg>
  );
}

export function OpenAIIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="256" height="260" preserveAspectRatio="xMidYMid" viewBox="0 0 256 260" id="openai">
      <path fill="#fff" d="M239.184 106.203a64.716 64.716 0 0 0-5.576-53.103C219.452 28.459 191 15.784 163.213 21.74A65.586 65.586 0 0 0 52.096 45.22a64.716 64.716 0 0 0-43.23 31.36c-14.31 24.602-11.061 55.634 8.033 76.74a64.665 64.665 0 0 0 5.525 53.102c14.174 24.65 42.644 37.324 70.446 31.36a64.72 64.72 0 0 0 48.754 21.744c28.481.025 53.714-18.361 62.414-45.481a64.767 64.767 0 0 0 43.229-31.36c14.137-24.558 10.875-55.423-8.083-76.483Zm-97.56 136.338a48.397 48.397 0 0 1-31.105-11.255l1.535-.87 51.67-29.825a8.595 8.595 0 0 0 4.247-7.367v-72.85l21.845 12.636c.218.111.37.32.409.563v60.367c-.056 26.818-21.783 48.545-48.601 48.601Zm-104.466-44.61a48.345 48.345 0 0 1-5.781-32.589l1.534.921 51.722 29.826a8.339 8.339 0 0 0 8.441 0l63.181-36.425v25.221a.87.87 0 0 1-.358.665l-52.335 30.184c-23.257 13.398-52.97 5.431-66.404-17.803ZM23.549 85.38a48.499 48.499 0 0 1 25.58-21.333v61.39a8.288 8.288 0 0 0 4.195 7.316l62.874 36.272-21.845 12.636a.819.819 0 0 1-.767 0L41.353 151.53c-23.211-13.454-31.171-43.144-17.804-66.405v.256Zm179.466 41.695-63.08-36.63L161.73 77.86a.819.819 0 0 1 .768 0l52.233 30.184a48.6 48.6 0 0 1-7.316 87.635v-61.391a8.544 8.544 0 0 0-4.4-7.213Zm21.742-32.69-1.535-.922-51.619-30.081a8.39 8.39 0 0 0-8.492 0L99.98 99.808V74.587a.716.716 0 0 1 .307-.665l52.233-30.133a48.652 48.652 0 0 1 72.236 50.391v.205ZM88.061 139.097l-21.845-12.585a.87.87 0 0 1-.41-.614V65.685a48.652 48.652 0 0 1 79.757-37.346l-1.535.87-51.67 29.825a8.595 8.595 0 0 0-4.246 7.367l-.051 72.697Zm11.868-25.58 28.138-16.217 28.188 16.218v32.434l-28.086 16.218-28.188-16.218-.052-32.434Z"></path>
    </svg>
  );
}

export function GeminiIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  const gradId = `gemini-grad-${size}`;
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="296" height="298" fill="none" viewBox="0 0 296 298" id="gemini">
      <mask id="a" width="296" height="298" x="0" y="0" maskUnits="userSpaceOnUse" style={{maskType: 'alpha'}}>
        <path fill="#3186FF" d="M141.201 4.886c2.282-6.17 11.042-6.071 13.184.148l5.985 17.37a184.004 184.004 0 0 0 111.257 113.049l19.304 6.997c6.143 2.227 6.156 10.91.02 13.155l-19.35 7.082a184.001 184.001 0 0 0-109.495 109.385l-7.573 20.629c-2.241 6.105-10.869 6.121-13.133.025l-7.908-21.296a184 184 0 0 0-109.02-108.658l-19.698-7.239c-6.102-2.243-6.118-10.867-.025-13.132l20.083-7.467A183.998 183.998 0 0 0 133.291 26.28l7.91-21.394Z"></path>
      </mask>
      <g mask="url(#a)">
        <g filter="url(#b)">
          <ellipse cx="163" cy="149" fill="#3689FF" rx="196" ry="159"></ellipse>
        </g>
        <g filter="url(#c)">
          <ellipse cx="33.5" cy="142.5" fill="#F6C013" rx="68.5" ry="72.5"></ellipse>
        </g>
        <g filter="url(#d)">
          <ellipse cx="19.5" cy="148.5" fill="#F6C013" rx="68.5" ry="72.5"></ellipse>
        </g>
        <g filter="url(#e)">
          <path fill="#FA4340" d="M194 10.5C172 82.5 65.5 134.333 22.5 135L144-66l50 76.5Z"></path>
        </g>
        <g filter="url(#f)">
          <path fill="#FA4340" d="M190.5-12.5C168.5 59.5 62 111.333 19 112L140.5-89l50 76.5Z"></path>
        </g>
        <g filter="url(#g)">
          <path fill="#14BB69" d="M194.5 279.5C172.5 207.5 66 155.667 23 155l121.5 201 50-76.5Z"></path>
        </g>
        <g filter="url(#h)">
          <path fill="#14BB69" d="M196.5 320.5C174.5 248.5 68 196.667 25 196l121.5 201 50-76.5Z"></path>
        </g>
      </g>
      <defs>
        <filter id="b" width="464" height="390" x="-69" y="-46" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="18"></feGaussianBlur>
        </filter>
        <filter id="c" width="265" height="273" x="-99" y="6" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
        <filter id="d" width="265" height="273" x="-113" y="12" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
        <filter id="e" width="299.5" height="329" x="-41.5" y="-130" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
        <filter id="f" width="299.5" height="329" x="-45" y="-153" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
        <filter id="g" width="299.5" height="329" x="-41" y="91" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
        <filter id="h" width="299.5" height="329" x="-39" y="132" colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse">
          <feFlood floodOpacity="0" result="BackgroundImageFix"></feFlood>
          <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape"></feBlend>
          <feGaussianBlur result="effect1_foregroundBlur_69_17998" stdDeviation="32"></feGaussianBlur>
        </filter>
      </defs>
    </svg>
  );
}

export function GrokIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 34 34" fill="#FFFFFF" className={className}>
      <g transform="translate(0.5, 0.5)">
        <path d="M13.2371 21.0407L24.3186 12.8506C24.8619 12.4491 25.6384 12.6057 25.8973 13.2294C27.2597 16.5185 26.651 20.4712 23.9403 23.1851C21.2297 25.8989 17.4581 26.4941 14.0108 25.1386L10.2449 26.8843C15.6463 30.5806 22.2053 29.6665 26.304 25.5601C29.5551 22.3051 30.562 17.8683 29.6205 13.8673L29.629 13.8758C28.2637 7.99809 29.9647 5.64871 33.449 0.844576C33.5314 0.730667 33.6139 0.616757 33.6964 0.5L29.1113 5.09055V5.07631L13.2343 21.0436" />
        <path d="M10.9503 23.0313C7.07343 19.3235 7.74185 13.5853 11.0498 10.2763C13.4959 7.82722 17.5036 6.82767 21.0021 8.2971L24.7595 6.55998C24.0826 6.07017 23.215 5.54334 22.2195 5.17313C17.7198 3.31926 12.3326 4.24192 8.67479 7.90126C5.15635 11.4239 4.0499 16.8403 5.94992 21.4622C7.36924 24.9165 5.04257 27.3598 2.69884 29.826C1.86829 30.7002 1.0349 31.5745 0.36364 32.5L10.9474 23.0341" />
      </g>
    </svg>
  );
}

export function DeepSeekIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 60 60" fill="#4D6BFE" className={className}>
      <g transform="translate(2, 6)">
        <path d="M55.6128 3.4712c-.5953-.2917-.8517.2642-1.1998.5466-.1191.0911-.2198.2095-.3206.3188-.8701.9292-1.8867 1.5398-3.2148 1.4668-1.9417-.1094-3.5995.5012-5.065 1.9863-.3114-1.8313-1.3463-2.9248-2.9217-3.6262-.8242-.3645-1.6577-.729-2.2348-1.5217-.403-.5647-.5129-1.1934-.7144-1.813-.1283-.3735-.2565-.7563-.687-.8201-.4671-.0728-.6503.3188-.8335.647-.7327 1.3394-1.0166 2.8154-.9892 4.3096.0641 3.3621 1.4838 6.0406 4.3047 7.9449.3206.2187.403.4372.3023.7563-.1924.656-.4214 1.2937-.6228 1.9497-.1283.4192-.3207.5103-.7694.3279-1.5479-.6467-2.8852-1.6035-4.0667-2.7605-2.0058-1.9407-3.8193-4.0818-6.0815-5.7583-.5312-.3918-1.0625-.7561-1.6121-1.1025-2.3081-2.2412.3023-4.0818.9068-4.3003.6319-.2278.2198-1.0115-1.8227-1.0022-2.0425.009-3.9109.6924-6.2922 1.6035-.348.1367-.7145.2368-1.09.3188-2.1615-.4099-4.4055-.5012-6.7502-.2368-4.4147.4919-7.9408 2.5784-10.5328 6.1409C.1914 13.1289-.5413 17.9941.3563 23.0691c.9434 5.3481 3.6727 9.7761 7.8676 13.2385 4.3506 3.5896 9.3606 5.3481 15.0758 5.011 3.4713-.2004 7.3364-.665 11.6961-4.355 1.099.5467 2.2531.7652 4.1674.9292 1.4746.1367 2.8943-.0728 3.9933-.3005 1.7219-.3645 1.6029-1.959.9801-2.2505-5.0466-2.3506-3.9385-1.394-4.9459-2.1685 2.5645-3.0339 6.4297-6.1865 7.9409-16.4001.119-.8108.0183-1.3211 0-1.9771-.0092-.4008.0824-.5556.5404-.6013 1.2639-.1458 2.4912-.4919 3.6178-1.1115 3.2698-1.7857 4.5886-4.7195 4.9-8.2364.0459-.5376-.0091-1.0935-.577-1.3757ZM27.119 35.123c-4.8909-3.8447-7.263-5.1113-8.2431-5.0566-.9159.0547-.751 1.1025-.5496 1.7859.2107.6741.4855 1.1389.8701 1.731.2656.3918.4489.9748-.2655 1.4123-1.5754.9749-4.314-.3281-4.4423-.3918-3.1872-1.877-5.8525-4.3553-7.7302-7.7444-1.8135-3.262-2.8667-6.7605-3.0408-10.4961-.0458-.9019.2198-1.221 1.1174-1.3848 1.1815-.2187 2.3997-.2644 3.5812-.0913 4.9918.729 9.2415 2.9612 12.8043 6.4963 2.0333 2.0135 3.572 4.419 5.1566 6.7696 1.6852 2.4963 3.4987 4.8745 5.8068 6.8242.8151.6833 1.4654 1.2026 2.0882 1.5854-1.8775.2095-5.01.2552-7.1532-1.4397Z" />
      </g>
    </svg>
  );
}

export function MetaIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#1877F2" className={className}>
      <path d="M12 2C8.5 2 5 4.5 5 8.5c0 2.5 1.5 4.8 3.5 6.5.5.4 1 .8 1.5 1.2.3.2.6.5.8.8.2.3.3.6.3.9v3.6c0 .6.4 1 1 1s1-.4 1-1v-3.6c0-.3.1-.6.3-.9.2-.3.5-.5.8-.8.5-.4 1-.8 1.5-1.2 2-1.7 3.5-4 3.5-6.5C19 4.5 15.5 2 12 2zm0 12c-2.2 0-4-1.8-4-4s1.8-4 4-4 4 1.8 4 4-1.8 4-4 4z" />
    </svg>
  );
}

export function MistralIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 129 91" className={className}>
      <g fill="#FF8205">
        <rect x="18.292" y="0" width="18.293" height="18.123" fill="#FFD800" />
        <rect x="91.473" y="0" width="18.293" height="18.123" fill="#FFD800" />
        <rect x="18.292" y="18.121" width="36.586" height="18.123" fill="#FFAF00" />
        <rect x="73.181" y="18.121" width="36.586" height="18.123" fill="#FFAF00" />
        <rect x="18.292" y="36.243" width="91.476" height="18.122" fill="#FF8205" />
        <rect x="18.292" y="54.37" width="18.293" height="18.123" fill="#FA500F" />
        <rect x="54.883" y="54.37" width="18.293" height="18.123" fill="#FA500F" />
        <rect x="91.473" y="54.37" width="18.293" height="18.123" fill="#FA500F" />
        <rect x="0" y="72.504" width="54.89" height="18.123" fill="#E10500" />
        <rect x="73.181" y="72.504" width="54.89" height="18.123" fill="#E10500" />
      </g>
    </svg>
  );
}

export function NvidiaIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" id="nvidia">
      <path fill="#77B900" d="m8.948 14.408.001.001zM8.948 18.121v-1.247c-4.84-.605-6.492-5.983-6.492-5.983s2.164-3.222 6.5-3.561V6.155C4.153 6.547 0 10.642 0 10.642s2.35 6.856 8.948 7.479z"></path>
      <path fill="#77B900" d="M4.275 11.053s1.016 3.836 4.673 4.495v-1.14c-2.058-.704-2.738-3.134-2.738-3.134s1.202-1.442 2.73-1.255h.008V8.773a6.035 6.035 0 0 1 .796-.036c2.508 0 4 1.968 4 1.968l-2.04 1.728c-.91-1.54-1.219-2.217-2.747-2.404v4.38c.371.124.76.187 1.158.187 2.976 0 5.75-3.882 5.75-3.882s-2.571-3.526-6.493-3.401h-.004a6.489 6.489 0 0 0-.42.018v1.441l-.027.003.023-.001c-2.913.321-4.669 2.279-4.669 2.279z"></path>
      <path fill="#77B900" d="M24 4H8.948v2.155l.424-.027c5.45-.186 9.01 4.506 9.01 4.506s-4.08 5.003-8.33 5.003a6.36 6.36 0 0 1-1.095-.098v1.335c.3.035.61.063.91.063 3.957 0 6.82-2.039 9.593-4.443.459.374 2.34 1.273 2.73 1.665-2.633 2.226-8.772 4.016-12.253 4.016-.335 0-.653-.018-.971-.053V20H24V4z"></path>
    </svg>
  );
}

export function GroqIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 201 201" width={size} height={size} className={className}>
      <path fill="#F54F35" d="M0 0h201v201H0V0Z"/>
      <path fill="#FEFBFB" d="m128 49 1.895 1.52C136.336 56.288 140.602 64.49 142 73c.097 1.823.148 3.648.161 5.474l.03 3.247.012 3.482.017 3.613c.01 2.522.016 5.044.02 7.565.01 3.84.041 7.68.072 11.521.007 2.455.012 4.91.016 7.364l.038 3.457c-.033 11.717-3.373 21.83-11.475 30.547-4.552 4.23-9.148 7.372-14.891 9.73l-2.387 1.055c-9.275 3.355-20.3 2.397-29.379-1.13-5.016-2.38-9.156-5.17-13.234-8.925 3.678-4.526 7.41-8.394 12-12l3.063 2.375c5.572 3.958 11.135 5.211 17.937 4.625 6.96-1.384 12.455-4.502 17-10 4.174-6.784 4.59-12.222 4.531-20.094l.012-3.473c.003-2.414-.005-4.827-.022-7.241-.02-3.68 0-7.36.026-11.04-.003-2.353-.008-4.705-.016-7.058l.025-3.312c-.098-7.996-1.732-13.21-6.681-19.47-6.786-5.458-13.105-8.211-21.914-7.792-7.327 1.188-13.278 4.7-17.777 10.601C75.472 72.012 73.86 78.07 75 85c2.191 7.547 5.019 13.948 12 18 5.848 3.061 10.892 3.523 17.438 3.688l2.794.103c2.256.082 4.512.147 6.768.209v16c-16.682.673-29.615.654-42.852-10.848-8.28-8.296-13.338-19.55-13.71-31.277.394-9.87 3.93-17.894 9.562-25.875l1.688-2.563C84.698 35.563 110.05 34.436 128 49Z"/>
    </svg>
  );
}

export function CohereIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 75 75" className={className}>
      <path d="M24.3 44.7c2 0 6-.1 11.6-2.4 6.5-2.7 19.3-7.5 28.6-12.5 6.5-3.5 9.3-8.1 9.3-14.3C73.8 7 66.9 0 58.3 0h-36C10 0 0 10 0 22.3s9.4 22.4 24.3 22.4z" fill="#39594d" />
      <path d="M30.4 60c0-6 3.6-11.5 9.2-13.8l11.3-4.7C62.4 36.8 75 45.2 75 57.6 75 67.2 67.2 75 57.6 75H45.3c-8.2 0-14.9-6.7-14.9-15z" fill="#d18ee2" />
      <path d="M12.9 47.6C5.8 47.6 0 53.4 0 60.5v1.7C0 69.2 5.8 75 12.9 75c7.1 0 12.9-5.8 12.9-12.9v-1.7c-.1-7-5.8-12.8-12.9-12.8z" fill="#ff7759" />
    </svg>
  );
}

export function TencentIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" id="tencent">
      <path fill="#0052D9" fillRule="evenodd" d="M9.976 1L24 9.8l-10.587.015L10.723 23H5.489L8.18 9.8H3.244L1 5.4h8.077L9.976 1z" />
    </svg>
  );
}

export function PoolsideIcon({ className = 'shrink-0', size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 128 128" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M35.959 121.526C24.0818 115.732 14.4341 106.579 8.05066 95.0574C1.81473 83.7992 -0.879432 71.1 0.251828 58.3309C0.507952 55.4694 3.02886 53.3568 5.89156 53.6095C8.7489 53.864 10.8649 56.3873 10.6123 59.2505C9.66451 69.946 11.9251 80.5867 17.1503 90.021C21.6488 98.1439 28.092 104.861 35.9564 109.677L60.417 59.5137C50.8426 56.3249 42.8678 57.713 42.1501 57.8524C42.0448 57.8767 41.943 57.8938 41.8395 57.9145C39.4554 58.3137 37.1494 57.0107 36.2211 54.8443C34.94 52.4524 31.0936 46.6059 26.4383 44.3349C21.7831 42.0638 14.6085 42.7964 12.2989 43.2986C10.3515 43.7238 8.32488 42.9977 7.09485 41.4319C5.86482 39.866 5.62905 37.7304 6.50215 35.9399C21.9599 4.22118 60.3479 -8.99859 92.0614 6.47266C123.775 21.9439 136.981 60.3025 121.55 92.012C121.534 92.0443 121.518 92.0767 121.501 92.1126C106.016 123.796 67.6581 136.99 35.959 121.526ZM69.7599 64.0716L45.3011 114.231C69.9874 123.453 98.0784 113.207 110.924 89.9213C109.118 87.1266 105.95 83.1199 102.283 81.3311C97.5455 79.0197 90.6037 79.7768 88.2189 80.2779C87.8263 80.3712 87.435 80.4162 87.0416 80.4201C86.3368 80.4235 85.6217 80.2838 84.9355 79.9846C84.2241 79.6732 83.5808 79.2036 83.0615 78.5986C82.7647 78.2491 82.5194 77.8669 82.3222 77.4591C82.1689 77.1529 78.3756 69.7924 69.7563 64.0698L69.7599 64.0716ZM30.9948 34.9814C34.9779 36.9245 38.2192 40.0146 40.6431 42.9284C48.1391 31.4618 58.3119 22.8009 66.1701 17.2168C69.0902 15.1432 72.1137 13.2045 75.0253 11.5316C54.5716 7.23693 33.135 15.3431 20.7056 32.4098C23.9955 32.635 27.6265 33.3382 30.9948 34.9814ZM98.566 23.0203C99.0407 26.3451 99.3765 29.9182 99.5389 33.5001C99.9773 43.105 99.422 56.4087 95.0351 69.3476C98.694 69.4457 102.949 70.0927 106.842 71.9919C110.318 73.6878 113.232 76.2533 115.526 78.8142C121.381 58.4737 114.576 36.5278 98.5643 23.0239L98.566 23.0203ZM69.7958 52.1345C76.989 55.6436 82.1885 60.3121 85.7127 64.3368C91.4457 45.7079 88.9465 24.8611 86.8596 17.1403C79.4921 20.2488 61.5261 31.1118 50.3829 47.1013C55.7288 47.3994 62.6061 48.627 69.7958 52.1345Z" fill="#4137FF" />
    </svg>
  );
}

/* ─── Icon lookup by provider ──────────────────────────── */

export const PROVIDER_ICONS: Record<string, (props?: IconProps) => React.ReactNode> = {
  krait: (p) => <KraitIcon {...p} />,
  kraivor: (p) => <KraitIcon {...p} />,
  anthropic: (p) => <ClaudeIcon {...p} />,
  openai: (p) => <OpenAIIcon {...p} />,
  google: (p) => <GeminiIcon {...p} />,
  gemini: (p) => <GeminiIcon {...p} />,
  xai: (p) => <GrokIcon {...p} />,
  grok: (p) => <GrokIcon {...p} />,
  deepseek: (p) => <DeepSeekIcon {...p} />,
  meta: (p) => <MetaIcon {...p} />,
  llama: (p) => <MetaIcon {...p} />,
  mistral: (p) => <MistralIcon {...p} />,
  nvidia: (p) => <NvidiaIcon {...p} />,
  groq: (p) => <GroqIcon {...p} />,
  cohere: (p) => <CohereIcon {...p} />,
  tencent: (p) => <TencentIcon {...p} />,
  poolside: (p) => <PoolsideIcon {...p} />,
};

/* ─── Icon lookup by model ID ──────────────────────────── */

export const MODEL_ICONS: Record<string, (props?: IconProps) => React.ReactNode> = {
  'krait-2.0': (p) => <KraitIcon {...p} />,
  'claude-fable-5': (p) => <ClaudeIcon {...p} />,
  'claude-opus-4-8': (p) => <ClaudeIcon {...p} />,
  'claude-opus-4-7': (p) => <ClaudeIcon {...p} />,
  'claude-sonnet-5': (p) => <ClaudeIcon {...p} />,
  'claude-sonnet-4-6': (p) => <ClaudeIcon {...p} />,
  'gpt-5.6-sol': (p) => <OpenAIIcon {...p} />,
  'gpt-5.6-terra': (p) => <OpenAIIcon {...p} />,
  'gpt-5.5': (p) => <OpenAIIcon {...p} />,
  'gpt-5.4': (p) => <OpenAIIcon {...p} />,
  'gemini-3.5-flash': (p) => <GeminiIcon {...p} />,
  'gemini-3.1-pro': (p) => <GeminiIcon {...p} />,
  'deepseek-v4-pro': (p) => <DeepSeekIcon {...p} />,
  'grok-4.3': (p) => <GrokIcon {...p} />,
  'cohere-north-mini-code': (p) => <CohereIcon {...p} />,
  'nvidia-nemotron-ultra': (p) => <NvidiaIcon {...p} />,
  'nvidia-nemotron-super': (p) => <NvidiaIcon {...p} />,
  'nvidia-nemotron-nano': (p) => <NvidiaIcon {...p} />,
  'tencent-hy3': (p) => <TencentIcon {...p} />,
  'poolside-laguna-xs': (p) => <PoolsideIcon {...p} />,
  'poolside-laguna-m': (p) => <PoolsideIcon {...p} />,
  'google-gemma-4': (p) => <GeminiIcon {...p} />,
  'openai-gpt-oss': (p) => <OpenAIIcon {...p} />,
  'groq-qwen3-32b': (p) => <GroqIcon {...p} />,
  'groq-qwen3.6-27b': (p) => <GroqIcon {...p} />,
};

/* ─── Helper: get icon for any model/provider ───────────── */

export function getModelIconById(id: string, props?: IconProps): React.ReactNode {
  const iconFn = MODEL_ICONS[id];
  if (iconFn) return iconFn(props);
  // Fallback: try provider lookup
  const providerFn = PROVIDER_ICONS[id];
  if (providerFn) return providerFn(props);
  // Fallback: return null (caller renders default)
  return null;
}
