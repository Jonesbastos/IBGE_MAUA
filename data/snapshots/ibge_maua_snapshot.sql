BEGIN TRANSACTION;
CREATE TABLE bronze_ibge_raw (
    ibge_id INTEGER PRIMARY KEY,
    endpoint_url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL
);
INSERT INTO "bronze_ibge_raw" VALUES(3529401,'https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3529401','{"id": 3529401, "microrregiao": {"id": 35061, "mesorregiao": {"UF": {"id": 35, "nome": "São Paulo", "regiao": {"id": 3, "nome": "Sudeste", "sigla": "SE"}, "sigla": "SP"}, "id": 3515, "nome": "Metropolitana de São Paulo"}, "nome": "São Paulo"}, "nome": "Mauá", "regiao-imediata": {"id": 350001, "nome": "São Paulo", "regiao-intermediaria": {"UF": {"id": 35, "nome": "São Paulo", "regiao": {"id": 3, "nome": "Sudeste", "sigla": "SE"}, "sigla": "SP"}, "id": 3501, "nome": "São Paulo"}}}','2026-11-02T02:59:46.960302+00:00',200,'011f3f4253adf42bc5a48dc1c5ed3d804c77d53ea50f0e6c9ee57a7541d509e9');
CREATE TABLE bronze_ibge_socioeconomico (
    municipio_id INTEGER NOT NULL,
    indicador TEXT NOT NULL,
    periodo_referencia TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
    PRIMARY KEY (municipio_id, indicador, periodo_referencia)
);
INSERT INTO "bronze_ibge_socioeconomico" VALUES(3529401,'censo_pop_area_densidade','2022','Censo Demográfico 2022 (Agregado 4714)','https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93|6318|614?localidades=N6[3529401]','[{"id":"93","resultados":[{"classificacoes":[],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"418261"}}]}],"unidade":"Pessoas","variavel":"População residente"},{"id":"6318","resultados":[{"classificacoes":[],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"61.937"}}]}],"unidade":"Quilômetros quadrados","variavel":"Área da unidade territorial"},{"id":"614","resultados":[{"classificacoes":[],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"6753.01"}}]}],"unidade":"Habitante por quilômetro quadrado","variavel":"Densidade demográfica"}]','52e06a22d3f70b68cda96a6d1c6bb6fb7d21da1ec2f2598adceebc4bd977f3c0',200,'2026-11-02T02:59:47.210449+00:00');
INSERT INTO "bronze_ibge_socioeconomico" VALUES(3529401,'populacao_estimada_historica','2001-2026','Estimativas de População (Agregado 6579)','https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/all/variaveis/9324?localidades=N6[3529401]','[{"id":"9324","resultados":[{"classificacoes":[],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2001":"371475","2002":"377782","2003":"384461","2004":"398482","2005":"406242","2006":"413943","2008":"412753","2009":"417458","2011":"421184","2012":"425169","2013":"444136","2014":"448776","2015":"453286","2016":"457696","2017":"462005","2018":"468148","2019":"472912","2020":"477552","2021":"481725","2024":"429380","2025":"429014","2026":"429064"}}]}],"unidade":"Pessoas","variavel":"População residente estimada"}]','042355e7dc0c21de0da705141c717dd39d43c51b5e75f05b2c1177f95e5d3988',200,'2026-11-02T02:59:47.241815+00:00');
INSERT INTO "bronze_ibge_socioeconomico" VALUES(3529401,'pib_municipal_historico','2002-2023','Produto Interno Bruto dos Municípios (Pesquisa 38)','https://servicodados.ibge.gov.br/api/v1/pesquisas/38/resultados/3529401','[{"id":46999,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":"2705826","2000":"3339281","2001":"3299814","2002":"3704371","2003":"4244284","2004":"4711863","2005":"4772722","2006":"5099726","2007":"5359927","2008":"5676425","2009":"6574530","2010":"7350831","2011":"7592184","2012":"7863726","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47018,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":"241","2000":"274","2001":"398","2002":"631","2003":"667","2004":"719","2005":"579","2006":"695","2007":"819","2008":"675","2009":"875","2010":"685","2011":"704","2012":"715","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47019,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":"939217","2000":"1340385","2001":"1291705","2002":"1471900","2003":"1760869","2004":"1989382","2005":"1911849","2006":"1898111","2007":"2004935","2008":"1944579","2009":"2348182","2010":"2578398","2011":"2539340","2012":"2439809","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47020,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":"1302670","2000":"1450648","2001":"1430466","2002":"1638006","2003":"1828197","2004":"1978755","2005":"2184423","2006":"2448862","2007":"2617762","2008":"2866074","2009":"3337802","2010":"3704736","2011":"3949474","2012":"4316518","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47024,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":"463698","2000":"547974","2001":"577246","2002":"593835","2003":"654552","2004":"743007","2005":"675871","2006":"752057","2007":"736411","2008":"865097","2009":"887671","2010":"1067012","2011":"1102667","2012":"1106684","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47023,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"798481","2003":"847296","2004":"949326","2005":"925502","2006":"1017292","2007":"1016878","2008":"1258413","2009":"1265514","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47014,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"1266231","2003":"1471599","2004":"1588189","2005":"1756749","2006":"2012358","2007":"2132783","2008":"2456379","2009":"2779207","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47015,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"374588","2003":"410623","2004":"445505","2005":"519512","2006":"581545","2007":"661729","2008":"715952","2009":"850453","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":46998,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"3886495","2003":"4633684","2004":"5147944","2005":"5524969","2006":"5962360","2007":"6386846","2008":"7273015","2009":"7939876","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47010,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"3088014","2003":"3786388","2004":"4198618","2005":"4599468","2006":"4945068","2007":"5369968","2008":"6014602","2009":"6674362","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47012,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"336","2003":"373","2004":"359","2005":"375","2006":"514","2007":"513","2008":"520","2009":"704","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47013,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":"1446858","2003":"1903793","2004":"2164565","2005":"2322832","2006":"2350651","2007":"2574944","2008":"2841750","2009":"3043998","2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]},{"id":47022,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"1523332","2011":"1660118","2012":"1712561","2013":"1863202","2014":"1799931.49","2015":"1874494.27","2016":"1881860.23","2017":"2205955.16","2018":"2269410.26","2019":"2365921.104","2020":"2421374.861","2021":"3272943.928","2022":null,"2023":null}}]},{"id":47001,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"22343.28","2011":"23298.86","2012":"21862.74","2013":"23639.95","2014":"24947.60","2015":"26407.17","2016":"31766.96","2017":"35747.87","2018":"32655.92","2019":"34433.94","2020":"35584.74","2021":"43128.78","2022":"57646.93","2023":"59773.04"}}]},{"id":47004,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"7800093","2011":"8152990","2012":"7582799","2013":"8636152","2014":"9395950.78","2015":"10095506.49","2016":"12657749.79","2017":"14309741.71","2018":"13018393.39","2019":"13918301.404","2020":"14572187.63","2021":"17503268.817","2022":null,"2023":null}}]},{"id":47008,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"3329124","2011":"3985790","2012":"4092545","2013":"4695763","2014":"5063664.06","2015":"5519960.72","2016":"5844463.95","2017":"6670111.58","2018":"6551065.43","2019":"6993760.643","2020":"7146483.05","2021":"7936387.777","2022":null,"2023":null}}]},{"id":46997,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"9323424","2011":"9813108","2012":"9295360","2013":"10499354","2014":"11195882.27","2015":"11970000.76","2016":"14539610.02","2017":"16515696.87","2018":"15287803.65","2019":"16284222.508","2020":"16993562.491","2021":"20776212.745","2022":"24111460.53","2023":"25000732.02"}}]},{"id":47006,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"932","2011":"925","2012":"1081","2013":"1337","2014":"657.64","2015":"775.30","2016":"609.66","2017":"17.31","2018":"13.88","2019":"14.518","2020":"18.56","2021":"22.476","2022":null,"2023":null}}]},{"id":47007,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"3607277","2011":"3257826","2012":"2517027","2013":"2788988","2014":"3112872.52","2015":"3254146.38","2016":"5464239.98","2017":"6232240.33","2018":"4989842.60","2019":"5385863.215","2020":"5668143.258","2021":"7756771.51","2022":null,"2023":null}}]},{"id":47009,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":"862760","2011":"908449","2012":"972146","2013":"1150064","2014":"1218756.56","2015":"1320624.09","2016":"1348436.20","2017":"1407372.49","2018":"1477471.48","2019":"1538663.027","2020":"1757542.761","2021":"1810087.054","2022":null,"2023":null}}]},{"id":47002,"res":[{"localidade":"352940","notas":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":null,"2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null},"res":{"1999":null,"2000":null,"2001":null,"2002":null,"2003":null,"2004":null,"2005":null,"2006":null,"2007":null,"2008":null,"2009":null,"2010":null,"2011":null,"2012":"18495.53","2013":null,"2014":null,"2015":null,"2016":null,"2017":null,"2018":null,"2019":null,"2020":null,"2021":null,"2022":null,"2023":null}}]}]','bba08b7304e1a5c077b8677439969dd6ee395f782e56018388a2b879001998a5',200,'2026-11-02T02:59:47.279349+00:00');
INSERT INTO "bronze_ibge_socioeconomico" VALUES(3529401,'censo_alfabetizacao','2022','Censo Demográfico 2022 (Agregado 9543)','https://servicodados.ibge.gov.br/api/v3/agregados/9543/periodos/2022/variaveis/2513?localidades=N6[3529401]','[{"id":"2513","resultados":[{"classificacoes":[{"categoria":{"6794":"Total"},"id":"2","nome":"Sexo"},{"categoria":{"95251":"Total"},"id":"86","nome":"Cor ou raça"},{"categoria":{"100362":"Total"},"id":"287","nome":"Idade"}],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"96.74"}}]}],"unidade":"%","variavel":"Taxa de alfabetização das pessoas de 15 anos ou mais de idade"}]','f2123b5d8a474dc901ce1096e7721008552e3de03613250e53a09a15fcbebe13',200,'2026-11-02T02:59:47.311126+00:00');
INSERT INTO "bronze_ibge_socioeconomico" VALUES(3529401,'censo_sexo','2022','Censo Demográfico 2022 (Agregado 9514)','https://servicodados.ibge.gov.br/api/v3/agregados/9514/periodos/2022/variaveis/93?localidades=N6[3529401]&classificacao=2[4,5]|287[100362]','[{"id":"93","resultados":[{"classificacoes":[{"categoria":{"4":"Homens"},"id":"2","nome":"Sexo"},{"categoria":{"100362":"Total"},"id":"287","nome":"Idade"},{"categoria":{"113635":"Total"},"id":"286","nome":"Forma de declaração da idade"}],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"201348"}}]},{"classificacoes":[{"categoria":{"5":"Mulheres"},"id":"2","nome":"Sexo"},{"categoria":{"100362":"Total"},"id":"287","nome":"Idade"},{"categoria":{"113635":"Total"},"id":"286","nome":"Forma de declaração da idade"}],"series":[{"localidade":{"id":"3529401","nivel":{"id":"N6","nome":"Município"},"nome":"Mauá (SP)"},"serie":{"2022":"216913"}}]}],"unidade":"Pessoas","variavel":"População residente"}]','edef5a5550b969126b98267f2d402153b9bc42b1f951eac48c0e59b1d7db4d4b',200,'2026-11-02T02:59:47.339530+00:00');
CREATE TABLE silver_ibge_censitario (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    variavel_id INTEGER NOT NULL,
    variavel_nome TEXT NOT NULL,
    categoria_classificacao TEXT NOT NULL,
    valor REAL NOT NULL,
    unidade TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, variavel_id, categoria_classificacao)
);
INSERT INTO "silver_ibge_censitario" VALUES(3529401,2022,93,'População residente por sexo','Homens',201348.0,'Pessoas','IBGE - Censo Demográfico 2022','censo_sexo','2026-11-02T02:59:47.620427+00:00');
INSERT INTO "silver_ibge_censitario" VALUES(3529401,2022,93,'População residente por sexo','Mulheres',216913.0,'Pessoas','IBGE - Censo Demográfico 2022','censo_sexo','2026-11-02T02:59:47.620427+00:00');
INSERT INTO "silver_ibge_censitario" VALUES(3529401,2022,614,'Densidade demográfica','Total',6753.01,'hab/km²','IBGE - Censo Demográfico 2022','censo_pop_area_densidade','2026-11-02T02:59:47.620427+00:00');
INSERT INTO "silver_ibge_censitario" VALUES(3529401,2022,2513,'Taxa de alfabetização','Total',96.74,'%','IBGE - Censo Demográfico 2022','censo_alfabetizacao','2026-11-02T02:59:47.620427+00:00');
INSERT INTO "silver_ibge_censitario" VALUES(3529401,2022,6318,'Área territorial','Total',61.937,'km²','IBGE - Censo Demográfico 2022','censo_pop_area_densidade','2026-11-02T02:59:47.620427+00:00');
CREATE TABLE silver_ibge_pib (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    indicador_id INTEGER NOT NULL,
    indicador_nome TEXT NOT NULL,
    valor REAL NOT NULL,
    unidade TEXT NOT NULL,
    tipo_valor TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, indicador_id)
);
INSERT INTO "silver_ibge_pib" VALUES(3529401,1999,46999,'Produto Interno Bruto a preços correntes (1999-2012)',2705826.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,1999,47018,'Valor adicionado bruto da agropecuária (1999-2012)',241.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,1999,47019,'Valor adicionado bruto da indústria (1999-2012)',939217.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,1999,47020,'Valor adicionado bruto dos serviços (1999-2012)',1302670.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,1999,47024,'Impostos sobre produtos (1999-2012)',463698.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2000,46999,'Produto Interno Bruto a preços correntes (1999-2012)',3339281.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2000,47018,'Valor adicionado bruto da agropecuária (1999-2012)',274.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2000,47019,'Valor adicionado bruto da indústria (1999-2012)',1340385.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2000,47020,'Valor adicionado bruto dos serviços (1999-2012)',1450648.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2000,47024,'Impostos sobre produtos (1999-2012)',547974.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2001,46999,'Produto Interno Bruto a preços correntes (1999-2012)',3299814.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2001,47018,'Valor adicionado bruto da agropecuária (1999-2012)',398.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2001,47019,'Valor adicionado bruto da indústria (1999-2012)',1291705.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2001,47020,'Valor adicionado bruto dos serviços (1999-2012)',1430466.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2001,47024,'Impostos sobre produtos (1999-2012)',577246.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,46998,'Produto Interno Bruto a preços correntes (2002-2009)',3886495.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,46999,'Produto Interno Bruto a preços correntes (1999-2012)',3704371.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47010,'Valor adicionado bruto da agropecuária (2002-2009)',3088014.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47012,'Valor adicionado bruto da indústria (2002-2009)',336.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47013,'Valor adicionado bruto dos serviços (2002-2009)',1446858.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47014,'Valor adicionado bruto da administração pública (2002-2009)',1266231.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47015,'Valor adicionado bruto total (2002-2009)',374588.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47018,'Valor adicionado bruto da agropecuária (1999-2012)',631.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47019,'Valor adicionado bruto da indústria (1999-2012)',1471900.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47020,'Valor adicionado bruto dos serviços (1999-2012)',1638006.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47023,'Impostos sobre produtos (2002-2009)',798481.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2002,47024,'Impostos sobre produtos (1999-2012)',593835.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,46998,'Produto Interno Bruto a preços correntes (2002-2009)',4633684.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,46999,'Produto Interno Bruto a preços correntes (1999-2012)',4244284.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47010,'Valor adicionado bruto da agropecuária (2002-2009)',3786388.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47012,'Valor adicionado bruto da indústria (2002-2009)',373.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47013,'Valor adicionado bruto dos serviços (2002-2009)',1903793.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47014,'Valor adicionado bruto da administração pública (2002-2009)',1471599.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47015,'Valor adicionado bruto total (2002-2009)',410623.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47018,'Valor adicionado bruto da agropecuária (1999-2012)',667.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47019,'Valor adicionado bruto da indústria (1999-2012)',1760869.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47020,'Valor adicionado bruto dos serviços (1999-2012)',1828197.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47023,'Impostos sobre produtos (2002-2009)',847296.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2003,47024,'Impostos sobre produtos (1999-2012)',654552.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,46998,'Produto Interno Bruto a preços correntes (2002-2009)',5147944.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,46999,'Produto Interno Bruto a preços correntes (1999-2012)',4711863.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47010,'Valor adicionado bruto da agropecuária (2002-2009)',4198618.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47012,'Valor adicionado bruto da indústria (2002-2009)',359.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47013,'Valor adicionado bruto dos serviços (2002-2009)',2164565.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47014,'Valor adicionado bruto da administração pública (2002-2009)',1588189.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47015,'Valor adicionado bruto total (2002-2009)',445505.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47018,'Valor adicionado bruto da agropecuária (1999-2012)',719.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47019,'Valor adicionado bruto da indústria (1999-2012)',1989382.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47020,'Valor adicionado bruto dos serviços (1999-2012)',1978755.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47023,'Impostos sobre produtos (2002-2009)',949326.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2004,47024,'Impostos sobre produtos (1999-2012)',743007.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,46998,'Produto Interno Bruto a preços correntes (2002-2009)',5524969.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,46999,'Produto Interno Bruto a preços correntes (1999-2012)',4772722.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47010,'Valor adicionado bruto da agropecuária (2002-2009)',4599468.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47012,'Valor adicionado bruto da indústria (2002-2009)',375.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47013,'Valor adicionado bruto dos serviços (2002-2009)',2322832.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47014,'Valor adicionado bruto da administração pública (2002-2009)',1756749.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47015,'Valor adicionado bruto total (2002-2009)',519512.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47018,'Valor adicionado bruto da agropecuária (1999-2012)',579.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47019,'Valor adicionado bruto da indústria (1999-2012)',1911849.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47020,'Valor adicionado bruto dos serviços (1999-2012)',2184423.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47023,'Impostos sobre produtos (2002-2009)',925502.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2005,47024,'Impostos sobre produtos (1999-2012)',675871.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,46998,'Produto Interno Bruto a preços correntes (2002-2009)',5962360.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,46999,'Produto Interno Bruto a preços correntes (1999-2012)',5099726.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47010,'Valor adicionado bruto da agropecuária (2002-2009)',4945068.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47012,'Valor adicionado bruto da indústria (2002-2009)',514.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47013,'Valor adicionado bruto dos serviços (2002-2009)',2350651.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47014,'Valor adicionado bruto da administração pública (2002-2009)',2012358.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47015,'Valor adicionado bruto total (2002-2009)',581545.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47018,'Valor adicionado bruto da agropecuária (1999-2012)',695.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47019,'Valor adicionado bruto da indústria (1999-2012)',1898111.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47020,'Valor adicionado bruto dos serviços (1999-2012)',2448862.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47023,'Impostos sobre produtos (2002-2009)',1017292.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2006,47024,'Impostos sobre produtos (1999-2012)',752057.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,46998,'Produto Interno Bruto a preços correntes (2002-2009)',6386846.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,46999,'Produto Interno Bruto a preços correntes (1999-2012)',5359927.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47010,'Valor adicionado bruto da agropecuária (2002-2009)',5369968.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47012,'Valor adicionado bruto da indústria (2002-2009)',513.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47013,'Valor adicionado bruto dos serviços (2002-2009)',2574944.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47014,'Valor adicionado bruto da administração pública (2002-2009)',2132783.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47015,'Valor adicionado bruto total (2002-2009)',661729.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47018,'Valor adicionado bruto da agropecuária (1999-2012)',819.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47019,'Valor adicionado bruto da indústria (1999-2012)',2004935.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47020,'Valor adicionado bruto dos serviços (1999-2012)',2617762.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47023,'Impostos sobre produtos (2002-2009)',1016878.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2007,47024,'Impostos sobre produtos (1999-2012)',736411.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,46998,'Produto Interno Bruto a preços correntes (2002-2009)',7273015.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,46999,'Produto Interno Bruto a preços correntes (1999-2012)',5676425.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47010,'Valor adicionado bruto da agropecuária (2002-2009)',6014602.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47012,'Valor adicionado bruto da indústria (2002-2009)',520.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47013,'Valor adicionado bruto dos serviços (2002-2009)',2841750.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47014,'Valor adicionado bruto da administração pública (2002-2009)',2456379.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47015,'Valor adicionado bruto total (2002-2009)',715952.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47018,'Valor adicionado bruto da agropecuária (1999-2012)',675.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47019,'Valor adicionado bruto da indústria (1999-2012)',1944579.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47020,'Valor adicionado bruto dos serviços (1999-2012)',2866074.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47023,'Impostos sobre produtos (2002-2009)',1258413.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2008,47024,'Impostos sobre produtos (1999-2012)',865097.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,46998,'Produto Interno Bruto a preços correntes (2002-2009)',7939876.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,46999,'Produto Interno Bruto a preços correntes (1999-2012)',6574530.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47010,'Valor adicionado bruto da agropecuária (2002-2009)',6674362.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47012,'Valor adicionado bruto da indústria (2002-2009)',704.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47013,'Valor adicionado bruto dos serviços (2002-2009)',3043998.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47014,'Valor adicionado bruto da administração pública (2002-2009)',2779207.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47015,'Valor adicionado bruto total (2002-2009)',850453.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47018,'Valor adicionado bruto da agropecuária (1999-2012)',875.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47019,'Valor adicionado bruto da indústria (1999-2012)',2348182.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47020,'Valor adicionado bruto dos serviços (1999-2012)',3337802.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47023,'Impostos sobre produtos (2002-2009)',1265514.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2009,47024,'Impostos sobre produtos (1999-2012)',887671.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,46997,'Produto Interno Bruto a preços correntes',9323424.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,46999,'Produto Interno Bruto a preços correntes (1999-2012)',7350831.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47001,'Produto Interno Bruto per capita',22343.28,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47004,'Valor adicionado bruto a preços correntes total',7800093.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47006,'Valor adicionado bruto da agropecuária',932.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47007,'Valor adicionado bruto da indústria',3607277.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47008,'Valor adicionado bruto dos serviços',3329124.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47009,'Valor adicionado bruto da administração pública',862760.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47018,'Valor adicionado bruto da agropecuária (1999-2012)',685.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47019,'Valor adicionado bruto da indústria (1999-2012)',2578398.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47020,'Valor adicionado bruto dos serviços (1999-2012)',3704736.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1523332.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2010,47024,'Impostos sobre produtos (1999-2012)',1067012.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,46997,'Produto Interno Bruto a preços correntes',9813108.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,46999,'Produto Interno Bruto a preços correntes (1999-2012)',7592184.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47001,'Produto Interno Bruto per capita',23298.86,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47004,'Valor adicionado bruto a preços correntes total',8152990.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47006,'Valor adicionado bruto da agropecuária',925.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47007,'Valor adicionado bruto da indústria',3257826.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47008,'Valor adicionado bruto dos serviços',3985790.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47009,'Valor adicionado bruto da administração pública',908449.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47018,'Valor adicionado bruto da agropecuária (1999-2012)',704.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47019,'Valor adicionado bruto da indústria (1999-2012)',2539340.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47020,'Valor adicionado bruto dos serviços (1999-2012)',3949474.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1660118.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2011,47024,'Impostos sobre produtos (1999-2012)',1102667.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,46997,'Produto Interno Bruto a preços correntes',9295360.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,46999,'Produto Interno Bruto a preços correntes (1999-2012)',7863726.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47001,'Produto Interno Bruto per capita',21862.74,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47002,'Produto Interno Bruto per capita (2012)',18495.53,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47004,'Valor adicionado bruto a preços correntes total',7582799.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47006,'Valor adicionado bruto da agropecuária',1081.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47007,'Valor adicionado bruto da indústria',2517027.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47008,'Valor adicionado bruto dos serviços',4092545.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47009,'Valor adicionado bruto da administração pública',972146.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47018,'Valor adicionado bruto da agropecuária (1999-2012)',715.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47019,'Valor adicionado bruto da indústria (1999-2012)',2439809.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47020,'Valor adicionado bruto dos serviços (1999-2012)',4316518.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1712561.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2012,47024,'Impostos sobre produtos (1999-2012)',1106684.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,46997,'Produto Interno Bruto a preços correntes',10499354.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47001,'Produto Interno Bruto per capita',23639.95,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47004,'Valor adicionado bruto a preços correntes total',8636152.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47006,'Valor adicionado bruto da agropecuária',1337.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47007,'Valor adicionado bruto da indústria',2788988.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47008,'Valor adicionado bruto dos serviços',4695763.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47009,'Valor adicionado bruto da administração pública',1150064.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2013,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1863202.0,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,46997,'Produto Interno Bruto a preços correntes',11195882.27,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47001,'Produto Interno Bruto per capita',24947.6,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47004,'Valor adicionado bruto a preços correntes total',9395950.78,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47006,'Valor adicionado bruto da agropecuária',657.64,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47007,'Valor adicionado bruto da indústria',3112872.52,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47008,'Valor adicionado bruto dos serviços',5063664.06,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47009,'Valor adicionado bruto da administração pública',1218756.56,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2014,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1799931.49,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,46997,'Produto Interno Bruto a preços correntes',11970000.76,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47001,'Produto Interno Bruto per capita',26407.17,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47004,'Valor adicionado bruto a preços correntes total',10095506.49,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47006,'Valor adicionado bruto da agropecuária',775.3,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47007,'Valor adicionado bruto da indústria',3254146.38,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47008,'Valor adicionado bruto dos serviços',5519960.72,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47009,'Valor adicionado bruto da administração pública',1320624.09,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2015,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1874494.27,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,46997,'Produto Interno Bruto a preços correntes',14539610.02,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47001,'Produto Interno Bruto per capita',31766.96,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47004,'Valor adicionado bruto a preços correntes total',12657749.79,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47006,'Valor adicionado bruto da agropecuária',609.66,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47007,'Valor adicionado bruto da indústria',5464239.98,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47008,'Valor adicionado bruto dos serviços',5844463.95,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47009,'Valor adicionado bruto da administração pública',1348436.2,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2016,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',1881860.23,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,46997,'Produto Interno Bruto a preços correntes',16515696.87,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47001,'Produto Interno Bruto per capita',35747.87,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47004,'Valor adicionado bruto a preços correntes total',14309741.71,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47006,'Valor adicionado bruto da agropecuária',17.31,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47007,'Valor adicionado bruto da indústria',6232240.33,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47008,'Valor adicionado bruto dos serviços',6670111.58,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47009,'Valor adicionado bruto da administração pública',1407372.49,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2017,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',2205955.16,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,46997,'Produto Interno Bruto a preços correntes',15287803.65,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47001,'Produto Interno Bruto per capita',32655.92,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47004,'Valor adicionado bruto a preços correntes total',13018393.39,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47006,'Valor adicionado bruto da agropecuária',13.88,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47007,'Valor adicionado bruto da indústria',4989842.6,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47008,'Valor adicionado bruto dos serviços',6551065.43,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47009,'Valor adicionado bruto da administração pública',1477471.48,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2018,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',2269410.26,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,46997,'Produto Interno Bruto a preços correntes',16284222.508,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47001,'Produto Interno Bruto per capita',34433.94,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47004,'Valor adicionado bruto a preços correntes total',13918301.404,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47006,'Valor adicionado bruto da agropecuária',14.518,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47007,'Valor adicionado bruto da indústria',5385863.215,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47008,'Valor adicionado bruto dos serviços',6993760.643,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47009,'Valor adicionado bruto da administração pública',1538663.027,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2019,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',2365921.104,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,46997,'Produto Interno Bruto a preços correntes',16993562.491,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47001,'Produto Interno Bruto per capita',35584.74,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47004,'Valor adicionado bruto a preços correntes total',14572187.63,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47006,'Valor adicionado bruto da agropecuária',18.56,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47007,'Valor adicionado bruto da indústria',5668143.258,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47008,'Valor adicionado bruto dos serviços',7146483.05,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47009,'Valor adicionado bruto da administração pública',1757542.761,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2020,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',2421374.861,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,46997,'Produto Interno Bruto a preços correntes',20776212.745,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47001,'Produto Interno Bruto per capita',43128.78,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47004,'Valor adicionado bruto a preços correntes total',17503268.817,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47006,'Valor adicionado bruto da agropecuária',22.476,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47007,'Valor adicionado bruto da indústria',7756771.51,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47008,'Valor adicionado bruto dos serviços',7936387.777,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47009,'Valor adicionado bruto da administração pública',1810087.054,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2021,47022,'Impostos, líquidos de subsídios, sobre produtos a preços correntes',3272943.928,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2022,46997,'Produto Interno Bruto a preços correntes',24111460.53,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2022,47001,'Produto Interno Bruto per capita',57646.93,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2023,46997,'Produto Interno Bruto a preços correntes',25000732.02,'Mil Reais','Corrente','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
INSERT INTO "silver_ibge_pib" VALUES(3529401,2023,47001,'Produto Interno Bruto per capita',59773.04,'Reais','Per Capita','IBGE - Produto Interno Bruto dos Municípios','pib_municipal_historico','2026-11-02T02:59:47.579455+00:00');
CREATE TABLE silver_ibge_populacao (
    municipio_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    populacao INTEGER NOT NULL,
    tipo_populacao TEXT NOT NULL,
    unidade TEXT NOT NULL,
    fonte_oficial TEXT NOT NULL,
    bronze_indicador TEXT NOT NULL,
    transformed_at TEXT NOT NULL,
    PRIMARY KEY (municipio_id, ano_referencia, tipo_populacao)
);
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2001,371475,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2002,377782,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2003,384461,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2004,398482,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2005,406242,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2006,413943,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2008,412753,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2009,417458,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2011,421184,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2012,425169,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2013,444136,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2014,448776,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2015,453286,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2016,457696,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2017,462005,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2018,468148,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2019,472912,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2020,477552,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2021,481725,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2022,418261,'Censo Demográfico','Pessoas','IBGE - Censo Demográfico 2022','censo_pop_area_densidade','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2024,429380,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2025,429014,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
INSERT INTO "silver_ibge_populacao" VALUES(3529401,2026,429064,'Estimativa Populacional','Pessoas','IBGE - Estimativas de População','populacao_estimada_historica','2026-11-02T02:59:47.544408+00:00');
CREATE TABLE silver_municipio (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    microrregiao_id INTEGER NOT NULL,
    microrregiao_nome TEXT NOT NULL,
    microrregiao_mesorregiao_id INTEGER NOT NULL,
    microrregiao_mesorregiao_nome TEXT NOT NULL,
    microrregiao_mesorregiao_uf_id INTEGER NOT NULL,
    microrregiao_mesorregiao_uf_sigla TEXT NOT NULL,
    microrregiao_mesorregiao_uf_nome TEXT NOT NULL,
    microrregiao_mesorregiao_uf_regiao_id INTEGER NOT NULL,
    microrregiao_mesorregiao_uf_regiao_sigla TEXT NOT NULL,
    microrregiao_mesorregiao_uf_regiao_nome TEXT NOT NULL,
    regiao_imediata_id INTEGER NOT NULL,
    regiao_imediata_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_sigla TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_nome TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_id INTEGER NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_sigla TEXT NOT NULL,
    regiao_imediata_regiao_intermediaria_uf_regiao_nome TEXT NOT NULL,
    transformed_at TEXT NOT NULL
);
INSERT INTO "silver_municipio" VALUES(3529401,'Mauá',35061,'São Paulo',3515,'Metropolitana de São Paulo',35,'SP','São Paulo',3,'SE','Sudeste',350001,'São Paulo',3501,'São Paulo',35,'SP','São Paulo',3,'SE','Sudeste','2026-11-02T02:59:47.025201+00:00');
CREATE VIEW gold_vw_municipio_hierarquia AS
SELECT
    id AS municipio_id,
    nome AS municipio_nome,
    microrregiao_mesorregiao_uf_id AS uf_id,
    microrregiao_mesorregiao_uf_sigla AS uf_sigla,
    microrregiao_mesorregiao_uf_nome AS uf_nome,
    microrregiao_mesorregiao_uf_regiao_id AS regiao_id,
    microrregiao_mesorregiao_uf_regiao_sigla AS regiao_sigla,
    microrregiao_mesorregiao_uf_regiao_nome AS regiao_nome,
    regiao_imediata_id AS regiao_imediata_id,
    regiao_imediata_nome AS regiao_imediata_nome,
    regiao_imediata_regiao_intermediaria_id AS regiao_intermediaria_id,
    regiao_imediata_regiao_intermediaria_nome AS regiao_intermediaria_nome,
    microrregiao_id AS microrregiao_id,
    microrregiao_nome AS microrregiao_nome,
    microrregiao_mesorregiao_id AS mesorregiao_id,
    microrregiao_mesorregiao_nome AS mesorregiao_nome,
    transformed_at
FROM silver_municipio;
CREATE VIEW gold_vw_qualidade_auditoria AS
SELECT
    b.ibge_id AS bronze_ibge_id,
    s.id AS silver_id,
    COALESCE(b.ibge_id, s.id) AS municipio_id,
    COALESCE(s.nome, 'NÃO DISPONÍVEL NA SILVER') AS municipio_nome,
    b.endpoint_url,
    b.http_status,
    b.checksum_sha256,
    b.ingestion_timestamp,
    s.transformed_at,
    CASE WHEN b.ibge_id IS NOT NULL THEN 1 ELSE 0 END AS flag_presente_bronze,
    CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END AS flag_presente_silver,
    CASE
        WHEN b.ibge_id IS NOT NULL AND s.id IS NOT NULL THEN 'CONFORME'
        WHEN b.ibge_id IS NOT NULL AND s.id IS NULL THEN 'AUSENTE_NA_SILVER'
        WHEN b.ibge_id IS NULL AND s.id IS NOT NULL THEN 'AUSENTE_NA_BRONZE'
        ELSE 'INDEFINIDO'
    END AS status_integracao,
    CASE
        WHEN (b.ibge_id BETWEEN 1000000 AND 9999999)
             OR (s.id BETWEEN 1000000 AND 9999999)
        THEN 1
        ELSE 0
    END AS flag_codigo_ibge_valido,
    CASE
        WHEN b.checksum_sha256 IS NOT NULL AND length(b.checksum_sha256) = 64
        THEN 1
        ELSE 0
    END AS flag_checksum_valido,
    CASE
        WHEN b.http_status = 200 THEN 1
        ELSE 0
    END AS flag_http_ok,
    CASE
        WHEN s.id IS NOT NULL AND (
            s.nome IS NULL OR trim(s.nome) = '' OR
            s.microrregiao_id IS NULL OR
            s.microrregiao_mesorregiao_uf_sigla IS NULL OR
            s.regiao_imediata_id IS NULL
        ) THEN 1
        ELSE 0
    END AS flag_campos_obrigatorios_nulos,
    CASE
        WHEN s.id IS NOT NULL AND (
            s.microrregiao_mesorregiao_uf_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_sigla
            AND s.microrregiao_mesorregiao_uf_regiao_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_regiao_sigla
        ) THEN 1
        WHEN s.id IS NOT NULL THEN 0
        ELSE NULL
    END AS flag_consistencia_geografica,
    CASE
        WHEN b.ingestion_timestamp IS NOT NULL AND s.transformed_at IS NOT NULL
        THEN ROUND(
            (julianday(s.transformed_at) - julianday(b.ingestion_timestamp)) * 86400.0,
            2
        )
        ELSE NULL
    END AS latencia_processamento_segundos
FROM bronze_ibge_raw b
LEFT JOIN silver_municipio s ON b.ibge_id = s.id

UNION ALL

SELECT
    NULL AS bronze_ibge_id,
    s.id AS silver_id,
    s.id AS municipio_id,
    s.nome AS municipio_nome,
    NULL AS endpoint_url,
    NULL AS http_status,
    NULL AS checksum_sha256,
    NULL AS ingestion_timestamp,
    s.transformed_at,
    0 AS flag_presente_bronze,
    1 AS flag_presente_silver,
    'AUSENTE_NA_BRONZE' AS status_integracao,
    CASE
        WHEN s.id BETWEEN 1000000 AND 9999999 THEN 1
        ELSE 0
    END AS flag_codigo_ibge_valido,
    0 AS flag_checksum_valido,
    0 AS flag_http_ok,
    CASE
        WHEN (
            s.nome IS NULL OR trim(s.nome) = '' OR
            s.microrregiao_id IS NULL OR
            s.microrregiao_mesorregiao_uf_sigla IS NULL OR
            s.regiao_imediata_id IS NULL
        ) THEN 1
        ELSE 0
    END AS flag_campos_obrigatorios_nulos,
    CASE
        WHEN (
            s.microrregiao_mesorregiao_uf_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_sigla
            AND s.microrregiao_mesorregiao_uf_regiao_sigla =
                s.regiao_imediata_regiao_intermediaria_uf_regiao_sigla
        ) THEN 1
        ELSE 0
    END AS flag_consistencia_geografica,
    NULL AS latencia_processamento_segundos
FROM silver_municipio s
WHERE s.id NOT IN (SELECT ibge_id FROM bronze_ibge_raw);
CREATE VIEW gold_populacao_historica AS
WITH pop_base AS (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.populacao,
        p.tipo_populacao,
        p.unidade,
        p.fonte_oficial,
        LAG(p.ano_referencia) OVER (
            PARTITION BY p.municipio_id, p.tipo_populacao
            ORDER BY p.ano_referencia
        ) AS ano_anterior,
        LAG(p.populacao) OVER (
            PARTITION BY p.municipio_id, p.tipo_populacao
            ORDER BY p.ano_referencia
        ) AS pop_anterior
    FROM silver_ibge_populacao p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    populacao,
    tipo_populacao,
    unidade,
    CASE
        WHEN pop_anterior IS NOT NULL THEN (populacao - pop_anterior)
        ELSE NULL
    END AS variacao_absoluta_anterior,
    CASE
        WHEN pop_anterior IS NOT NULL THEN
            ROUND(((populacao - pop_anterior) * 100.0) / NULLIF(pop_anterior, 0), 2)
        ELSE NULL
    END AS variacao_percentual_anterior,
    CASE
        WHEN ano_anterior IS NULL THEN NULL
        WHEN (ano_referencia - ano_anterior) = 1 THEN 1
        ELSE 0
    END AS flag_anos_consecutivos,
    fonte_oficial
FROM pop_base;
CREATE VIEW gold_pib_historico AS
WITH pib_pivot AS (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 46997 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 46998 THEN p.valor END)
        ) AS pib_corrente_mil_reais,
        MAX(CASE WHEN p.indicador_id = 47001 THEN p.valor END) AS pib_per_capita_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47006 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47010 THEN p.valor END)
        ) AS vab_agropecuaria_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47007 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47012 THEN p.valor END)
        ) AS vab_industria_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47008 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47013 THEN p.valor END)
        ) AS vab_servicos_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47009 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47014 THEN p.valor END)
        ) AS vab_administracao_publica_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47004 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47015 THEN p.valor END)
        ) AS vab_total_mil_reais,
        COALESCE(
            MAX(CASE WHEN p.indicador_id = 47022 THEN p.valor END),
            MAX(CASE WHEN p.indicador_id = 47023 THEN p.valor END)
        ) AS impostos_mil_reais,
        'IBGE - Produto Interno Bruto dos Municípios' AS fonte_oficial
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    GROUP BY p.municipio_id, m.nome, p.ano_referencia
),
pib_lag AS (
    SELECT
        *,
        LAG(pib_corrente_mil_reais) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS pib_anterior,
        LAG(pib_per_capita_reais) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS pib_per_capita_anterior,
        LAG(ano_referencia) OVER (
            PARTITION BY municipio_id ORDER BY ano_referencia
        ) AS ano_anterior
    FROM pib_pivot
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    pib_corrente_mil_reais,
    pib_per_capita_reais,
    vab_agropecuaria_mil_reais,
    vab_industria_mil_reais,
    vab_servicos_mil_reais,
    vab_administracao_publica_mil_reais,
    vab_total_mil_reais,
    impostos_mil_reais,
    'Mil Reais' AS unidade_pib,
    'Reais' AS unidade_per_capita,
    CASE
        WHEN pib_anterior IS NOT NULL
             AND (ano_referencia - ano_anterior) = 1 THEN
            ROUND(
                ((pib_corrente_mil_reais - pib_anterior) * 100.0)
                / NULLIF(pib_anterior, 0),
                2
            )
        ELSE NULL
    END AS variacao_nominal_pib_pct,
    CASE
        WHEN pib_per_capita_anterior IS NOT NULL
             AND (ano_referencia - ano_anterior) = 1 THEN
            ROUND(
                ((pib_per_capita_reais - pib_per_capita_anterior) * 100.0)
                / NULLIF(pib_per_capita_anterior, 0),
                2
            )
        ELSE NULL
    END AS variacao_nominal_per_capita_pct,
    ROUND(
        (vab_agropecuaria_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_agropecuaria_vab_pct,
    ROUND(
        (vab_industria_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_industria_vab_pct,
    ROUND(
        (vab_servicos_mil_reais * 100.0) / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_servicos_vab_pct,
    ROUND(
        (vab_administracao_publica_mil_reais * 100.0)
        / NULLIF(vab_total_mil_reais, 0),
        2
    ) AS participacao_administracao_publica_vab_pct,
    fonte_oficial
FROM pib_lag;
CREATE VIEW gold_demografia_sexo AS
WITH sexo_agg AS (
    SELECT
        c.municipio_id,
        m.nome AS municipio_nome,
        c.ano_referencia,
        MAX(
            CASE WHEN c.categoria_classificacao = 'Homens'
                 THEN c.valor END
        ) AS populacao_masculina,
        MAX(
            CASE WHEN c.categoria_classificacao = 'Mulheres'
                 THEN c.valor END
        ) AS populacao_feminina,
        c.fonte_oficial
    FROM silver_ibge_censitario c
    LEFT JOIN silver_municipio m ON c.municipio_id = m.id
    WHERE c.variavel_nome LIKE '%sexo%'
       OR c.categoria_classificacao IN ('Homens', 'Mulheres')
    GROUP BY c.municipio_id, m.nome, c.ano_referencia, c.fonte_oficial
)
SELECT
    municipio_id,
    municipio_nome,
    ano_referencia,
    CAST(populacao_masculina AS INTEGER) AS populacao_masculina,
    CAST(populacao_feminina AS INTEGER) AS populacao_feminina,
    CAST((populacao_masculina + populacao_feminina) AS INTEGER)
        AS populacao_total,
    ROUND(
        (populacao_masculina * 100.0)
        / NULLIF(populacao_masculina + populacao_feminina, 0),
        2
    ) AS participacao_masculina_pct,
    ROUND(
        (populacao_feminina * 100.0)
        / NULLIF(populacao_masculina + populacao_feminina, 0),
        2
    ) AS participacao_feminina_pct,
    ROUND(
        (populacao_masculina * 100.0) / NULLIF(populacao_feminina, 0),
        2
    ) AS razao_sexo,
    fonte_oficial
FROM sexo_agg;
CREATE VIEW gold_resumo_socioeconomico AS
SELECT
    p.municipio_id,
    m.nome AS municipio_nome,
    'Demografia' AS tema,
    'População residente total (Censo 2022)' AS indicador,
    p.populacao AS valor,
    p.unidade,
    p.ano_referencia,
    p.fonte_oficial,
    p.transformed_at
FROM silver_ibge_populacao p
LEFT JOIN silver_municipio m ON p.municipio_id = m.id
WHERE p.tipo_populacao = 'Censo Demográfico'

UNION ALL

SELECT
    p.municipio_id,
    m.nome AS municipio_nome,
    'Demografia' AS tema,
    'População residente estimada mais recente' AS indicador,
    p.populacao AS valor,
    p.unidade,
    p.ano_referencia,
    p.fonte_oficial,
    p.transformed_at
FROM silver_ibge_populacao p
LEFT JOIN silver_municipio m ON p.municipio_id = m.id
WHERE p.tipo_populacao = 'Estimativa Populacional'
  AND p.ano_referencia = (
      SELECT MAX(ano_referencia) FROM silver_ibge_populacao
      WHERE tipo_populacao = 'Estimativa Populacional'
  )

UNION ALL

SELECT
    c.municipio_id,
    m.nome AS municipio_nome,
    CASE
        WHEN c.variavel_nome LIKE '%sexo%' THEN 'Demografia'
        WHEN c.variavel_nome LIKE '%alfabetiz%' THEN 'Educação'
        ELSE 'Território'
    END AS tema,
    c.variavel_nome || CASE
        WHEN c.categoria_classificacao != 'Total'
        THEN ' (' || c.categoria_classificacao || ')'
        ELSE ''
    END AS indicador,
    c.valor,
    c.unidade,
    c.ano_referencia,
    c.fonte_oficial,
    c.transformed_at
FROM silver_ibge_censitario c
LEFT JOIN silver_municipio m ON c.municipio_id = m.id

UNION ALL

SELECT
    pib.municipio_id,
    pib.municipio_nome,
    'Economia' AS tema,
    'Produto Interno Bruto a preços correntes' AS indicador,
    pib.pib_corrente_mil_reais AS valor,
    pib.unidade_pib AS unidade,
    pib.ano_referencia,
    pib.fonte_oficial,
    pib.transformed_at
FROM (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.valor AS pib_corrente_mil_reais,
        p.unidade AS unidade_pib,
        p.fonte_oficial,
        p.transformed_at
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    WHERE p.indicador_id = 46997
      AND p.ano_referencia = (
          SELECT MAX(ano_referencia) FROM silver_ibge_pib WHERE indicador_id = 46997
      )
) pib

UNION ALL

SELECT
    pib.municipio_id,
    pib.municipio_nome,
    'Economia' AS tema,
    'Produto Interno Bruto per capita' AS indicador,
    pib.pib_per_capita_reais AS valor,
    pib.unidade_per_capita AS unidade,
    pib.ano_referencia,
    pib.fonte_oficial,
    pib.transformed_at
FROM (
    SELECT
        p.municipio_id,
        m.nome AS municipio_nome,
        p.ano_referencia,
        p.valor AS pib_per_capita_reais,
        p.unidade AS unidade_per_capita,
        p.fonte_oficial,
        p.transformed_at
    FROM silver_ibge_pib p
    LEFT JOIN silver_municipio m ON p.municipio_id = m.id
    WHERE p.indicador_id = 47001
      AND p.ano_referencia = (
          SELECT MAX(ano_referencia) FROM silver_ibge_pib WHERE indicador_id = 47001
      )
) pib;
COMMIT;
