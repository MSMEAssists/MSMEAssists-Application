import { createContext, useContext, useState, useEffect } from "react";

const LanguageContext = createContext();

export const TRANSLATIONS = {
  en: {
    home: "Home",
    schemes: "Schemes",
    about: "About",
    help: "Help",
    login: "Login",
    register: "Register",
    logout: "Sign Out",
    getStarted: "Get Started",
    heroEyebrow: "GOVERNMENT SCHEME RECOMMENDATIONS FOR MSMES",
    heroTitle: "Right Schemes. Real Growth.",
    heroSubtitle: "MSMEAssist helps Indian MSMEs discover relevant government schemes, check eligibility and understand the application process — all in one place.",
    pillar1: "Discover relevant schemes for your business",
    pillar2: "Check eligibility in minutes",
    pillar3: "Get step-by-step guidance",
    pillar4: "Access official government support",
    howTitle: "How MSMEAssist Helps You",
    howSubtitle: "We make government schemes simple, accessible and personalized for your business needs.",
    personalTitle: "Government Schemes, Made Personal",
    personalSubtitle: "Get recommendations based on your business profile, industry, turnover and growth needs.",
    dashboard: "Dashboard",
    chatAssistant: "Chat Assistant",
    report: "Report",
    businessProfile: "Business Profile",
  },
  te: {
    home: "హోమ్",
    schemes: "పథకాలు",
    about: "గురించి",
    help: "సహాయం",
    login: "లాగిన్",
    register: "నమోదు",
    logout: "లాగ్ అవుట్",
    getStarted: "ప్రారంభించండి",
    heroEyebrow: "MSMEల కోసం ప్రభుత్వ పథకాల సిఫార్సులు",
    heroTitle: "సరైన పథకాలు. నిజమైన వృద్ధి.",
    heroSubtitle: "భారతీయ MSMEలు సరైన ప్రభుత్వ పథకాలను గుర్తించడానికి, అర్హతను తనిఖీ చేయడానికి మరియు దరఖాస్తు ప్రక్రియను అర్థం చేసుకోవడానికి MSMEAssist సహాయపడుతుంది.",
    pillar1: "మీ వ్యాపారానికి అనువైన పథకాలను కనుగొనండి",
    pillar2: "కొద్ది నిమిషాల్లోనే అర్హతను తనిఖీ చేయండి",
    pillar3: "దశలవారీగా స్పష్టమైన మార్గదర్శకత్వం",
    pillar4: "అధికారిక ప్రభుత్వ మద్దతును పొందండి",
    howTitle: "MSMEAssist మీకు ఎలా సహాయపడుతుంది",
    howSubtitle: "ప్రభుత్వ పథకాలను మీ వ్యాపార అవసరాలకు సులభం, అందుబాటులో మరియు వ్యక్తిగతీకరించడం మా లక్ష్యం.",
    personalTitle: "ప్రభుత్వ పథకాలు, మీ వ్యాపారం కోసం ప్రత్యేకం",
    personalSubtitle: "మీ వ్యాపార వివరాలు, పరిశ్రమ, టర్నోవర్ మరియు అభివృద్ధి అవసరాలకు తగిన సిఫార్సులు పొందండి.",
    dashboard: "డ్యాష్‌బోర్డ్",
    chatAssistant: "సహాయక చాట్",
    report: "నివేదిక",
    businessProfile: "వ్యాపార ప్రొఫైల్",
  },
};

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    return localStorage.getItem("msmeassist_lang") || "en";
  });

  useEffect(() => {
    localStorage.setItem("msmeassist_lang", lang);
  }, [lang]);

  const t = (key) => TRANSLATIONS[lang]?.[key] || TRANSLATIONS.en[key] || key;

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      lang: "en",
      setLang: () => {},
      t: (key) => TRANSLATIONS.en[key] || key,
    };
  }
  return context;
}
