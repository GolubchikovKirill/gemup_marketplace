"use client"

import type { Metadata } from "next";
import { SetStateAction, useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import clipboardCopy from "clipboard-copy";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { SideNav } from "@/components/side-nav";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { PageHeader } from "@/components/headers/page-header";
import { Scripts } from "@/components/shared/scripts";
import { Dropdown } from "@/components/ui/dropdown";
import { generatedProxyList } from "@/data";
import { IDropdown } from "@/types/component";
import { ProxyProtocolType, ProxySessionType, IProxyProviderData, ProxyLocationType, ProxyFormatType, IProxyBaseData } from "@/types/data";
import { useProxyListStore, useProxySettingsStore } from "@/store/proxy";
import { getProxyStr, sleep } from "@/utils";

// export const metadata: Metadata = {
//   title: "GEMUPS",
//   description: "",
//   keywords: "",
//   openGraph: {
//     type: "website",
//     url: "",
//     description: "",
//     siteName: "",
//     images: "",
//   },
// };



export default function GeneratePage() {
  const { proxyList, setProxyList, getProxyList } = useProxyListStore((state) => state);
  const proxySettings = useProxySettingsStore((state) => state);
  const {
    providerList,
    protocol,
    count,
    format,
    locationType,
    country,
    state,
    city,
    sessionType,
    ttl,
    setValue
  } = proxySettings;

  const [isMoreOptionsVisible, setIsMoreOptionsVisible] = useState<boolean>(false);
  const [isProxiesCopied, setIsProxiesCopied] = useState<boolean>(false);
  const [proxyStrList, setProxyStrList] = useState<string[]>(
    proxyList.map((proxy) => getProxyStr(proxy, format))
  );
  
  // const [proxyProtocol, setProxyProtocol] = useState<ProxyProtocolType>(protocol);
  // const [proxySessionType, setProxySessionType] = useState<ProxySessionType>(sessionType);
  // const [proxyCount, setProxyCount] = useState<number>(count);
  // const [proxyLocationType, setProxyLocationType] = useState<ProxyLocationType>(locationType);

  const [proxyProviderList, setProxyProviderList] = useState<IProxyProviderData[]>([
    { id: uuidv4(), isActive: false, icon: "/img/flag/poland.svg", name: "Lola", tag: "1234" },
    { id: uuidv4(), isActive: false, icon: "/img/icons/planet--green.svg", name: "Lola", tag: "1234" },
    { id: uuidv4(), isActive: false, name: "Bob" },
    { id: uuidv4(), isActive: false, name: "Paul" },
  ]);

  const [proxyFormatList, setProxyFormatList] = useState<IDropdown["list"]>([
    { id: uuidv4(), isActive: true, label: "ip:port:login:password" },
    { id: uuidv4(), isActive: false, label: "ip:port@login:password" },
    { id: uuidv4(), isActive: false, label: "login:password@ip:port" },
    { id: uuidv4(), isActive: false, label: "login:password:ip:port" }
  ]);

  const [proxyCountryList, setProxyCountryList] = useState<IDropdown["list"]>([
    { id: uuidv4(), isActive: true, label: "Poland" },
    { id: uuidv4(), isActive: false, label: "France" },
    { id: uuidv4(), isActive: false, label: "Germany" },
    { id: uuidv4(), isActive: false, label: "USA" }
  ]);

  const [proxyStateList, setProxyStateList] = useState<IDropdown["list"]>([
    { id: uuidv4(), isActive: true, label: "State" },
    { id: uuidv4(), isActive: false, label: "State" },
    { id: uuidv4(), isActive: false, label: "State" },
    { id: uuidv4(), isActive: false, label: "State" }
  ]);

  const [proxyCityList, setProxyCityList] = useState<IDropdown["list"]>([
    { id: uuidv4(), isActive: true, label: "City" },
    { id: uuidv4(), isActive: false, label: "City" },
    { id: uuidv4(), isActive: false, label: "City" },
    { id: uuidv4(), isActive: false, label: "City" }
  ]);

  const [proxyTtlList, setProxyTtlList] = useState<IDropdown["list"]>([
    { id: "ttl-3600", isActive: true, label: "60 min" },
    { id: "ttl-1800", isActive: false, label: "30 min" },
    { id: "ttl-900", isActive: false, label: "15 min" },
    { id: "ttl-300", isActive: false, label: "5 min" },
    { id: "ttl-60", isActive: false, label: "1 min" },
    { id: "ttl-30", isActive: false, label: "30 sec" },
  ]);

  // useEffect(() => {
  //   getProxyList();
  // }, []);

  useEffect(() => {
    const providerNameList = providerList.map((item) => item.name)

    setProxyProviderList(
      proxyProviderList.map((item) => ({
        ...item,
        isActive: providerNameList.includes(item.name)
      }))
    );
  }, [providerList]);

  useEffect(() => {
    setProxyFormatList(
      proxyFormatList.map((item) => ({ ...item, isActive: item.label === format }))
    );
  }, [format]);

  useEffect(() => {
    setProxyCountryList(
      proxyCountryList.map((item) => ({ ...item, isActive: item.label === country }))
    );
  }, [country]);

  useEffect(() => {
    setProxyStateList(
      proxyStateList.map((item) => ({ ...item, isActive: item.label === state }))
    );
  }, [state]);

  useEffect(() => {
    setProxyCityList(
      proxyCityList.map((item) => ({ ...item, isActive: item.label === city }))
    );
  }, [city]);

  useEffect(() => {
    setProxyTtlList(
      proxyTtlList.map((item) => ({ ...item, isActive: item.label === ttl }))
    );
  }, [ttl]);

  const handleProxiesCopy = async () => {
    await clipboardCopy(
      proxyList.map((proxy) => getProxyStr(proxy, format)).join("\n")
    );

    setIsProxiesCopied(true);
    await sleep(500);
    setIsProxiesCopied(false);

  }

  const handleSelectProxyProvider = (id: string | number) => {
    setProxyProviderList(
      proxyProviderList.map((item) => ({
        ...item,
        isActive: item.id === id ? !item.isActive : item.isActive
      }))
    )
  };

  const handleSaveSettings = () => {
    const activeItemData = {
      providerList: proxyProviderList.filter((item) => item.isActive),
      format: proxyFormatList.find((item) => item.isActive)?.label || format,
      country: proxyCountryList.find((item) => item.isActive)?.label || country,
      state: proxyStateList.find((item) => item.isActive)?.label || state,
      city: proxyCityList.find((item) => item.isActive)?.label || city,
      ttl: proxyTtlList.find((item) => item.isActive)?.label || ttl
    }

    setValue("providerList", activeItemData.providerList);
    setValue("format", activeItemData.format as ProxyFormatType);
    setValue("country", activeItemData.country);
    setValue("state", activeItemData.state);
    setValue("city", activeItemData.city);
    
    setProxyList([]);
    getProxyList(proxySettings);
  };

  return (
    <div className="page__wrapper generate-page">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <Breadcrumbs name="Generate proxy" />
          <PageHeader name="Generate proxy" />
          <section id="tabData">
            <div className="tabs container">
              <div className="tabs__nav">
                <button className="tabs__button active" data-tab="Residential">
                  Residential
                </button>
                <button className="tabs__button" data-tab="DataCenter">
                  Data Center
                </button>
                <button className="tabs__button" data-tab="ISP">
                  ISP
                </button>
              </div>
              <div className="tabs__content">
                <div className="tab active" id="Residential">
                  <div className="innerContent__wrapper">
                    <div className="mainContent">
                      <div className="generate-page__settings-box generate-page__settings-box--top box">
                        <div className="box__column">
                          <h3 className="box__column-title">
                            <span>Available proxy providers&nbsp;:</span>
                            <img src="/img/icons/hint.svg" alt="hint" />
                          </h3>
                          <div className="box__btn-list">
                            {proxyProviderList.map(({ id, isActive, icon, name, tag }) => (
                              <button
                                type="button"
                                className={`box__btn ${isActive && "active"}`}
                                onClick={() => handleSelectProxyProvider(id)}
                              >
                                {icon &&
                                  <img
                                    className="box__btn-icon"
                                    src={icon}
                                    alt="Poland"
                                    data-title="Poland"
                                  />
                                }
                                <span className="box__btn-caption">{name}</span>
                                {tag && <span className="box__btn-tag">#{tag}</span>}
                              </button>
                            ))}
                          </div>
                        </div>
                        <div className="box__column">
                          <h3 className="box__column-title">
                            <span>Protocol:&nbsp;</span>
                            <img src="/img/icons/hint.svg" alt="hint" />
                          </h3>
                          <div className="box__btn-list">
                            <button
                              type="button"
                              className={`box__btn ${protocol === "HTTPS" && "active"}`}
                              onClick={() => setValue("protocol", "HTTPS")}
                            >
                              <span className="box__btn-caption">HTTP(S)</span>
                            </button>
                            <button
                              type="button"
                              className={`box__btn ${protocol === "SOCKS5" && "active"}`}
                              onClick={() => setValue("protocol", "SOCKS5")}
                            >
                              <span className="box__btn-caption">SOCKS5</span>
                            </button>
                          </div>
                        </div>
                        <div className="panel-box__row box__row">
                          <div className="generate-page__count-panel generate-page__panel-box">
                            <h3 className="box__column-title">
                              <span>Count:&nbsp;</span>
                              <img src="/img/icons/hint.svg" alt="hint" />
                            </h3>
                            <div className="generate-page__panel-box-row">
                              <button
                                id="minus"
                                className="minus-btn"
                                data-input-id="generate-proxy-count-input"
                                onClick={() => setValue("count", count === 0 ? 0 : count - 1)}
                              ></button>
                              <input
                                id="generate-proxy-count-input"
                                className="generate-page__count-panel-input"
                                type="number"
                                value={count}
                                onChange={(e) => setValue("count", parseInt(e.target.value) < 0 ? 0 : parseInt(e.target.value))}
                              />
                              <button
                                id="plus"
                                className="plus-btn"
                                data-input-id="generate-proxy-count-input"
                                onClick={() => setValue("count", count + 1)}
                              ></button>
                            </div>
                          </div>
                          <div className="generate-page__format-panel generate-page__panel-box">
                            <h3 className="box__column-title">
                              <span>Format:&nbsp;</span>
                              <img src="/img/icons/hint.svg" alt="hint" />
                            </h3>
                            <Dropdown
                              id="generate-proxy-format-dropdown"
                              className="generate-page__format-panel-dropdown"
                              list={proxyFormatList}
                              setList={setProxyFormatList}
                              enableIcon
                            />
                          </div>
                          <div className="generate-page__more-options-panel generate-page__panel-box">
                            <span></span>
                            <button
                              id="show-more-options"
                              className="box__btn box__btn--light"
                              onClick={() => setIsMoreOptionsVisible(!isMoreOptionsVisible)}
                            >
                              {isMoreOptionsVisible ? "Hide" : "Show"} more options
                            </button>
                          </div>
                        </div>
                      </div>
                      {isMoreOptionsVisible &&
                        <div className="generate-page__settings-box generate-page__settings-box--bottom box">
                          <div className="box__column">
                            <h3 className="box__column-title">
                              <span>Location:&nbsp;</span>
                              <img src="/img/icons/hint.svg" alt="hint" />
                            </h3>
                            <div className="generate-page__location-panel box__row">
                              <div className="generate-page__location-panel-btn-list box__btn-list">
                                <button
                                  className={`box__btn ${locationType === "Random" && "active"}`}
                                  type="button"
                                  onClick={() => setValue("locationType", "Random")}
                                >
                                  Random
                                </button>
                                <button
                                  className={`box__btn ${locationType === "Country" && "active"}`}
                                  type="button"
                                  onClick={() => setValue("locationType", "Country")}
                                >
                                  Country
                                </button>
                              </div>
                              <div className="generate-page__location-panel-dropdown-list dropdown-list dropdown-list--row">
                                <Dropdown
                                  id="generate-proxy-country-dropdown"
                                  className="generate-page__location-panel-dropdown"
                                  caption="Country"
                                  list={proxyCountryList}
                                  setList={setProxyCountryList}
                                  enableIcon
                                  disabled={locationType === "Random"}
                                />
                                <Dropdown
                                  id="generate-proxy-state-dropdown"
                                  className="generate-page__location-panel-dropdown"
                                  caption="State"
                                  list={proxyStateList}
                                  setList={setProxyStateList}
                                  enableIcon
                                  disabled={locationType === "Random"}
                                />
                                <Dropdown
                                  id="generate-proxy-city-dropdown"
                                  className="generate-page__location-panel-dropdown"
                                  caption="City"
                                  list={proxyCityList}
                                  setList={setProxyCityList}
                                  enableIcon
                                  disabled={locationType === "Random"}
                                />
                              </div>
                            </div>
                          </div>
                          <div className="box__row">
                            <div className="generate-page__session-panel generate-page__panel-box">
                              <h3 className="box__column-title">
                                <span>Session type:&nbsp;</span>
                                <img src="/img/icons/hint.svg" alt="hint" />
                              </h3>
                              <div className="generate-page__session-panel-btn-list box__btn-list">
                                <button
                                  type="button"
                                  className={`box__btn ${sessionType === "Dynamic" && "active"}`}
                                  onClick={() => setValue("sessionType", "Dynamic")}
                                >
                                  Dynamic
                                </button>
                                <button
                                  type="button"
                                  className={`box__btn ${sessionType === "Static" && "active"}`}
                                  onClick={() => setValue("sessionType", "Static")}
                                >
                                  Static
                                </button>
                              </div>
                            </div>
                            <div className="generate-page__ttl-panel generate-page__panel-box">
                              <h3 className="box__column-title">
                                <span>TTL:&nbsp;</span>
                                <img src="/img/icons/hint.svg" alt="hint" />
                              </h3>
                              <Dropdown
                                id="generate-proxy-ttl-dropdown"
                                className="generate-page__ttl-panel-dropdown"
                                list={proxyTtlList}
                                setList={setProxyTtlList}
                                enableIcon
                              />
                            </div>
                            <div className="generate-page__panel-box">
                              <span></span>
                              <button
                                id="save-and-close"
                                className="box__btn bg--green color--black hover hover--opacity"
                                onClick={handleSaveSettings}
                              >
                                Save and close
                              </button>
                            </div>
                          </div>
                        </div>
                      }
                    </div>
                    <div className="sideData">
                      <div className="side__content">
                        <div className="Canv__wrapper" id="chartContainer">
                          <canvas
                            id="chartTraffic"
                            data-max="1000"
                            data-value="387"
                            data-line1="Traffic used"
                            data-total="/ 10 gb"
                          ></canvas>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="generated__area">
                    <div className="top__head">
                      <div className="title">{proxyList.filter((proxy) => proxy.type === protocol).length} proxy generated</div>
                      <button
                        type="button"
                        className="genCopy"
                        style={isProxiesCopied ? { backgroundColor: "#07462E" } : undefined}
                        onClick={handleProxiesCopy}
                      >
                        {isProxiesCopied ? "Copied" : "Copy"}<i className="ico-copy"></i>
                      </button>
                    </div>
                    <div className="generated__list">
                      {proxyList
                        .filter((proxy) => proxy.type === protocol)
                        .map((proxy, idx) => (
                        <div className="list__item" key={uuidv4()}>
                          <span className="number">{idx + 1}</span>
                          <span className="value">{getProxyStr(proxy, format)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="tab" id="DataCenter"></div>
              </div>
            </div>
          </section>
        </main>

        <Footer />
        <Scripts />
      </div>
    </div>
  );
}