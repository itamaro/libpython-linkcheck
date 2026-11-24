# Appendix: affected projects

Part of the [libpython link survey](README.md). Each project name links to
the wheel inspected: the Linux wheel for the newest Python in the project's
latest stable release ([method](method.md)). "Affected / extensions" counts
the Python extensions in that wheel whose own `DT_NEEDED` entries name
libpython, out of all Python extensions in it.

## Latest-release sample: 117 projects

### Affected wheels for Python 3.11 or newer: 74 projects

| Project (inspected wheel) | Version | Python | Affected / extensions | Direct dependency |
| --- | --- | --- | ---: | --- |
| [ace-fhe](https://files.pythonhosted.org/packages/a6/36/24b0ba378a6b2a5797257703d91608fef500e4dc6467729b9aa7f6381d3c/ace_fhe-0.2.2-cp312-cp312-manylinux_2_39_x86_64.whl) | 0.2.2 | cp312 | 1 / 2 | `libpython3.12.so.1.0` |
| [agx-openplx](https://files.pythonhosted.org/packages/1e/59/504db20441ff39c183bd4e34ca31ef78fd491fddfaefc844ce59c849a97b/agx_openplx-0.16.10-cp312-cp312-manylinux_2_39_x86_64.whl) | 0.16.10 | cp312 | 13 / 13 | `libpython3.12.so.1.0` |
| [ansiformatter](https://files.pythonhosted.org/packages/a6/90/4d777a3329c7c90828986365edd4d306e9959ff92b383f3a1db6f25090b6/ansiformatter-0.1.0-cp312-cp312-manylinux2014_aarch64.whl) | 0.1.0 | cp312 | 4 / 4 | `libpython3.12.so.1.0` |
| [babitmf](https://files.pythonhosted.org/packages/9a/e8/3db4a045aed0c44cb87d882c29b4ccbfdada7cb74f1cf9f9aabf338fd594/BabitMF-0.2.0-cp312-cp312-manylinux_2_28_x86_64.whl) | 0.2.0 | cp312 | 2 / 2 | `libpython3.12.so.1.0` |
| [babitmf-gpu](https://files.pythonhosted.org/packages/38/62/628dc0f51becd80108867e89dd95a911625fd35a5b09ceac6f412ea48648/BabitMF_GPU-0.2.0-cp312-cp312-manylinux_2_28_x86_64.whl) | 0.2.0 | cp312 | 2 / 2 | `libpython3.12.so.1.0` |
| [bow-api](https://files.pythonhosted.org/packages/70/cb/511332d145e9d828d5e6eab3d1b7f63aa31acb9f2c39dcee88b7fc7fcff9/bow_api-4.3.0.2831-cp313-none-manylinux2010_x86_64.whl) | 4.3.0.2831 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [bow-client](https://files.pythonhosted.org/packages/91/79/afe1027dcad4cdd28fd65f0940b4b064c15746988c0cccbd9b6869cbead9/bow_client-4.0.2.2269-cp311-none-manylinux2014_x86_64.whl) | 4.0.2.2269 | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [brion](https://files.pythonhosted.org/packages/cb/af/dbc7c384e72932dcdc96ba84615b22ca25ccdf78f753e522e2bad1b6c9dd/brion-3.3.10-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) | 3.3.10 | cp311 | 1 / 1 | `libpython3-72114d11.11.so.1.0` |
| [degirum](https://files.pythonhosted.org/packages/82/09/05ad1f1ba4a92c8a919191c5291c193e02e7a994ad2cec2e5edd8f58d250/degirum-1.6.1-cp314-cp314-manylinux_2_35_x86_64.whl) | 1.6.1 | cp314 | 1 / 3 | `libpython3.14.so.1.0` |
| [degirum-headless](https://files.pythonhosted.org/packages/51/eb/ace2a92f370ceb24dd066e250a3c47403ac97318ea7beacae9e68356f0a7/degirum_headless-0.15.3-cp312-cp312-manylinux_2_31_x86_64.whl) | 0.15.3 | cp312 | 1 / 3 | `libpython3.12.so.1.0` |
| [devart-access-connector](https://files.pythonhosted.org/packages/a0/3b/1fec9d899348bdf3c6fc304d2eb3d7e7d5b0e7ccfd08992bc676eda5ac6b/devart_access_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-ase-connector](https://files.pythonhosted.org/packages/05/f3/8877c58c5d8ce00c738fc84d42c396c826785132e0a40bea8aef836c9ac6/devart_ase_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-bigcommerce-connector](https://files.pythonhosted.org/packages/46/85/67ae26d363818b9c83a8af922fba352996a0fc42c2186e89488b4fccafca/devart_bigcommerce_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-dynamics365-connector](https://files.pythonhosted.org/packages/d2/4d/e75f43797a862f25a8ea60c9354d2acb6ac5adbcad055b6304a2626bab82/devart_dynamics365_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-excel-connector](https://files.pythonhosted.org/packages/90/10/d5890e353cfae0c94eb27f4d31a94d77c54189d84469b787bdc2ea5e9e01/devart_excel_connector-1.3.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.3.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-firebird-connector](https://files.pythonhosted.org/packages/37/6d/394ed127acc86eb33eee71aeb1d3b77d3e8aba2d8983cb985736ca8da1ca/devart_firebird_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-interbase-connector](https://files.pythonhosted.org/packages/31/c8/2cad25ea1a80802082ff26cbbb1a08f1f5c247a4271a04248124a959cdee/devart_interbase_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-mongodb-connector](https://files.pythonhosted.org/packages/80/79/889032397c511ffc25365e65ff86f450b52f0d743192167fcfc0572343f5/devart_mongodb_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-mysql-connector](https://files.pythonhosted.org/packages/3a/a3/d425c4e1d709e09f49f7731c47827c963fa2ce7615e54ce78b427c901477/devart_mysql_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-oracle-connector](https://files.pythonhosted.org/packages/49/2f/8406eb1e29c6f457fa1efa23a6cd6c4651b72430ab207901c2c14d687486/devart_oracle_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-postgresql-connector](https://files.pythonhosted.org/packages/8b/ae/e4f4633fd2d18741ed05ffe929070ef755d0c44d658ba80fa0db256b98b1/devart_postgresql_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-salesforce-connector](https://files.pythonhosted.org/packages/38/7f/15df39ef0d28b9e0fe059ee48dc19d2e0e1e534e16afa7c2db3dbaf5058b/devart_salesforce_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-sqlite-connector](https://files.pythonhosted.org/packages/ec/0f/b9e398c97a9ec829ae8d0266b62b9b08a4025740e11b0e4bbbdd5e254849/devart_sqlite_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-sqlserver-connector](https://files.pythonhosted.org/packages/5c/21/691aea5ebe3ba3294670b4e613a51573d9a68485c35148a6e185148560bd/devart_sqlserver_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [devart-xbase-connector](https://files.pythonhosted.org/packages/b0/ee/b9c6d4d62193a7cc4509c52ff51e24b94f217e6731877af7b2437e95acf5/devart_xbase_connector-1.4.0-cp315-cp315-manylinux_2_34_x86_64.whl) | 1.4.0 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [eegvizlib](https://files.pythonhosted.org/packages/3d/16/c8d517da70d4ddfa4383781cafd4ce5c2c622aa90fd0a08973b6a7abbe79/eegvizlib-0.2.0-cp314-abi3-manylinux_2_24_x86_64.whl) | 0.2.0 | cp314-abi3 | 1 / 1 | `libpython3.14.so.1.0` |
| [excel-copy-check](https://files.pythonhosted.org/packages/09/34/0bed6fc541003660e31f259b294b079e2a92b4d7e3acfaa4758d54ac7c04/excel_copy_check-0.1.0-cp314-cp314-manylinux_2_35_x86_64.whl) | 0.1.0 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [falcorcomp](https://files.pythonhosted.org/packages/ba/c8/4aab7d7f52c5da77a4f5c58aa9723429cc551a0a424e9464249716777764/falcorcomp-0.2.2-cp313-cp313-manylinux_2_35_x86_64.whl) | 0.2.2 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [fast-pysqlparse](https://files.pythonhosted.org/packages/47/d5/5bbb0274d2d94b08bd1c8c8eef6c7eef48002b4d794103acc54d51484fd7/fast_pysqlparse-0.8.6-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl) | 0.8.6 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [fastcrypto](https://files.pythonhosted.org/packages/39/8c/cdfc038c0eac168cf4bb3d57cffa10e9e1f872a8b301468941e3b011fa75/fastcrypto-0.0.3-cp312-cp312-manylinux2014_x86_64.whl) | 0.0.3 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [genicam](https://files.pythonhosted.org/packages/38/ff/a8c90b9a7d99fa6008437491f1198264c22d49572a0013a05bc1c579e034/genicam-1.6.0-cp314-cp314-manylinux2014_x86_64.whl) | 1.6.0 | cp314 | 2 / 2 | `libpython3.14.so.1.0` |
| [glaxnimate](https://files.pythonhosted.org/packages/14/80/ef0b93865ee1361fb759feec2f50e434e24848b856857edf31b1120fc1a1/glaxnimate-0.6.0.3-py3-none-manylinux1_x86_64.whl) | 0.6.0.3 | py3 | 1 / 1 | `libpython3.13.so.1.0` |
| [gmsm](https://files.pythonhosted.org/packages/3d/90/c1178652cbab8be0b99ae33bc1ad33173dff5c0de8f8d25372332d79bed8/gmsm-1.4.5-cp314-cp314-manylinux2014_x86_64.whl) | 1.4.5 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [goose-ir](https://files.pythonhosted.org/packages/72/7d/e2dea1968aea3169e2dec3e530fd5146dda9126a3862918b74cfa78a9f44/goose_ir-0.2.5-cp313-cp313-manylinux1_x86_64.whl) | 0.2.5 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [ikomia](https://files.pythonhosted.org/packages/98/53/3da5b87baac4ed8778471ec3f4f80df3230872a601ab3525665dd3e5ff19/ikomia-0.16.1-cp313-none-manylinux_2_35_x86_64.whl) | 0.16.1 | cp313 | 4 / 5 | `libpython3.13.so.1.0` |
| [ilwis](https://files.pythonhosted.org/packages/e2/1f/2bbca3519c167b733182c9d69730999f0f0687d64cbf274eebd092bead85/ilwis-1.0.20261019-cp314-cp314-manylinux_2_31_x86_64.whl) | 1.0.20261019 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [isaacsim-asset](https://files.pythonhosted.org/packages/41/d9/ef553e40b7f347ca59088fcfcd867cde6290a0134b7ac264f16683a209e6/isaacsim_asset-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 2 / 2 | `libpython3.12.so.1.0` |
| [isaacsim-core](https://files.pythonhosted.org/packages/8a/60/fe3104fdb84c68cf0df17011f1d07cd833c3e87f4c76a64c36646d69be94/isaacsim_core-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 4 / 9 | `libpython3.12.so.1.0` |
| [isaacsim-extscache-kit-sdk](https://files.pythonhosted.org/packages/30/22/d6b908631f80efb18ff3738aad05e6fe5836238cabbcf386baca43069eb7/isaacsim_extscache_kit_sdk-6.2.0.0-cp312-none-manylinux_2_35_aarch64.whl) | 6.2.0.0 | cp312 | 5 / 10 | `libpython3.12.so.1.0` |
| [isaacsim-extscache-physics](https://files.pythonhosted.org/packages/1b/ff/ed01b9f1d2a011e75a7de176647b98e2f393c18b635654d26b127f9641b2/isaacsim_extscache_physics-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 14 / 15 | `libpython3.12.so.1.0` |
| [isaacsim-kernel](https://files.pythonhosted.org/packages/b5/31/a5ad5948cf9f8c6dd95028716be9f9b0310f59ab4ef80974fd4e7a7c5bdf/isaacsim_kernel-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 3 / 36 | `libpython3.10.so.1.0`, `libpython3.11.so.1.0`, `libpython3.12.so.1.0` |
| [isaacsim-ros2](https://files.pythonhosted.org/packages/2f/70/ee1a79b4e7d0a23116d642664eacc258fe1f7ad05664029bf7c1654c8774/isaacsim_ros2-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 98 / 212 | `libpython3.12.so.1.0` |
| [isaacsim-sensor](https://files.pythonhosted.org/packages/20/06/12947c06b64665260ac44baa8e7a8161400feba261e50c431c23ff464e44/isaacsim_sensor-6.2.0.0-cp312-none-manylinux_2_35_x86_64.whl) | 6.2.0.0 | cp312 | 2 / 8 | `libpython3.12.so.1.0` |
| [isystem-connect](https://files.pythonhosted.org/packages/37/4f/5417ba782b9894fc2fb2b05041614454e62755376287e09251ddfcf5c6de/isystem_connect-9.26.22.5.319749-cp314-none-manylinux1_x86_64.whl) | 9.26.22.5.319749 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [jaack](https://files.pythonhosted.org/packages/ee/2a/f6040a6562e10230ff128f87c57d20d7922dec3557d49911168c4ded2777/jaack-1.0.11-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl) | 1.0.11 | cp313 | 1 / 1 | `libpython3.13.so` |
| [kya-validator](https://files.pythonhosted.org/packages/1a/50/94ae0eec3789a1e360dd35d4d727d0fb2a78ab965085b9714b87882230a9/kya_validator-0.2.3-cp312-cp312-manylinux_2_34_x86_64.whl) | 0.2.3 | cp312 | 1 / 1 | `libpython3-7310c6bf.12.so.1.0` |
| [libroadrunner](https://files.pythonhosted.org/packages/87/b0/8323be66accd699fb40a4cb68b64de52bdbfd180b44e146881abd5b79765/libroadrunner-2.11.0-cp315-cp315-manylinux_2_28_x86_64.whl) | 2.11.0 | cp315 | 4 / 4 | `libpython3.15.so.1.0` |
| [maixpy](https://files.pythonhosted.org/packages/ec/b3/416a4cb9891a99f0cf11cc9e34afd1cf460a4412bc4c0480051d940be3ac/maixpy-4.12.5-cp313-cp313-manylinux2014_x86_64.whl) | 4.12.5 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [nn-sdk](https://files.pythonhosted.org/packages/c6/df/59520cb211431c9882faa6198f51f232399c8b1f343c098c2129ea268d3c/nn_sdk-1.8.26-cp311-cp311-manylinux2014_x86_64.whl) | 1.8.26 | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [omniverse-kit](https://files.pythonhosted.org/packages/31/d2/721f9c6e5668b96849449611b703a23bc91989b36c56d8c3d7ca89cffaae/omniverse_kit-110.4.1.392751-cp312-none-manylinux_2_35_x86_64.whl) | 110.4.1.392751 | cp312 | 3 / 36 | `libpython3.10.so.1.0`, `libpython3.11.so.1.0`, `libpython3.12.so.1.0` |
| [onboardapipython](https://files.pythonhosted.org/packages/a0/fa/73293f102168daba50807afd18d7f8a9cd7c743e89d61966bbeba9d55e60/onboardapipython-9.10.0-cp314-none-manylinux2014_x86_64.whl) | 9.10.0 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [openyuanrong-datasystem](https://files.pythonhosted.org/packages/4c/0f/1d13b518aca0acdbe9ba81a4edc010a4424251abf2abd75d66010ae51258/openyuanrong_datasystem-0.8.1-cp312-cp312-manylinux_2_34_x86_64.whl) | 0.8.1 | cp312 | 1 / 2 | `libpython3.12.so.1.0` |
| [oximedia](https://files.pythonhosted.org/packages/ca/dd/a6573a5a5cc67ed3bf0c97e6d632b2a46c1c88efbd8574bb678bb3c7f26d/oximedia-0.2.0-cp313-cp313-manylinux_2_34_x86_64.whl) | 0.2.0 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [pureai-chunk](https://files.pythonhosted.org/packages/c6/65/88237a92982acc8b4729cf26f47d6fab783b8cfc5c8099c46efb6eb4846c/pureai_chunk-0.0.1-cp311-none-manylinux_2_17_x86_64.whl) | 0.0.1 | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [pymdzcf](https://files.pythonhosted.org/packages/43/69/23410d7b8daabb13e0753d8a4a7f733fabe57aab524938a472bb1b51e750/pymdzcf-0.1.0-cp312-cp312-manylinux_2_34_x86_64.whl) | 0.1.0 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [qairt-visualizer](https://files.pythonhosted.org/packages/80/08/9a1940860478ea04f01e862f90be671ccf61764fc094eb5c95fcc478eefc/qairt_visualizer-0.12.1-py3-none-manylinux2014_x86_64.whl) | 0.12.1 | py3 | 10 / 10 | `libpython3.10.so.1.0`, `libpython3.12.so.1.0` |
| [rafina](https://files.pythonhosted.org/packages/52/e2/dfc46fd092dafd6a92418db6a385a8693aba05d919c7d135d6765947cf85/rafina-0.0.9-py313-none-manylinux_2_28_x86_64.whl) | 0.0.9 | py313 | 1 / 1 | `libpython3.13.so.1.0` |
| [relab](https://files.pythonhosted.org/packages/f2/7e/740224a9fa2c5e839cb41d0a040fe88c17b220170307f979b4c62a80dfe4/relab-0.5.3-cp312-cp312-manylinux_2_39_x86_64.whl) | 0.5.3 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [rti-connext](https://files.pythonhosted.org/packages/60/59/fd4588d80c9ae5cd3df847e4d47350ef99fa68a0e802f4dbbd7d9a5ca825/rti_connext-7.7.0.1-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl) | 7.7.0.1 | cp314 | 1 / 2 | `libpython3.14.so.1.0` |
| [sambanova-rdu-engine-api](https://files.pythonhosted.org/packages/ad/b4/9f3ab666a81c0c49b77fe2312b903c97557debf843f8078079bc6e936488/sambanova_rdu_engine_api-1.27.0.post1-cp311-cp311-manylinux_2_28_x86_64.whl) | 1.27.0.post1 | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [se-import](https://files.pythonhosted.org/packages/c2/0d/4b858628b371521e560aba764e48c4b8411cfc8011a4427f14e2f069b76b/se_import-0.0.9-cp312-cp312-manylinux2014_x86_64.whl) | 0.0.9 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [silabs-mltk](https://files.pythonhosted.org/packages/c7/50/37c96344b2115c5ca3a21c57c40715a166b6328d256f232eaa04f022819f/silabs_mltk-0.20.0-1712091506-cp312-cp312-manylinux2014_x86_64.whl) | 0.20.0 | cp312 | 1 / 3 | `libpython3.12.so.1.0` |
| [slidgnal](https://files.pythonhosted.org/packages/7d/3c/ac6e15d46cebc3a164b4281128a9077c70b4e713f3a7311a1caa99324799/slidgnal-0.5.0-cp314-cp314-manylinux_2_41_x86_64.whl) | 0.5.0 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [spinepy](https://files.pythonhosted.org/packages/bf/75/741149918fe0d807f7c146206a3823927b03be792587ebf1f3a35c0e7f41/spinepy-0.0.3-cp312-cp312-manylinux2014_x86_64.whl) | 0.0.3 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [talyn](https://files.pythonhosted.org/packages/3a/e2/8d64ed6c7a5656b363feaa19cc6311a7e931d61eae711421a61f9b9f58cc/talyn-0.11.5-cp315-cp315-manylinux_2_36_x86_64.whl) | 0.11.5 | cp315 | 1 / 1 | `libpython3.15.so.1.0` |
| [tfrecords](https://files.pythonhosted.org/packages/bf/ed/9102411720c3b8dfd81b4035e34e47e896242c54f7586541cead61f5f4d1/tfrecords-0.3.1-cp314-cp314-manylinux2014_x86_64.whl) | 0.3.1 | cp314 | 2 / 2 | `libpython3.14.so.1.0` |
| [torch-xla](https://files.pythonhosted.org/packages/92/e7/46d863ac26f19a8d866bb2e8a1f06a675b9dfdd9b6fb417d244f2f9ebe7c/torch_xla-2.9.0-cp313-cp313-manylinux_2_28_x86_64.whl) | 2.9.0 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [turboml-bindings](https://files.pythonhosted.org/packages/45/9c/21d078973da636c59893d09a3e7dd42ad571c22051d6eb9694557a71a9df/turboml_bindings-0.1.4-py311-none-manylinux_2_35_x86_64.whl) | 0.1.4 | py311 | 2 / 2 | `libpython3.11.so.1.0` |
| [tvpynt](https://files.pythonhosted.org/packages/ab/3f/948ac3d80b293dd20f9e52087df8e212a7f27d5bb95b87bc63cb72002a49/tvpynt-0.1.4-cp313-cp313-manylinux2014_x86_64.whl) | 0.1.4 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [tvpynt-bundled](https://files.pythonhosted.org/packages/1c/00/d9b344155bb80db4f0cae279552ec582967284ac670a7f7bf40fb66c6be8/tvpynt_bundled-0.1.4-cp313-cp313-manylinux2014_x86_64.whl) | 0.1.4 | cp313 | 1 / 1 | `libpython3.13.so.1.0` |
| [ubpe-cython](https://files.pythonhosted.org/packages/a4/89/0e0d06b95bce0509b894ef792b7559f89c26728400431c1d2ecb8fd700b5/ubpe_cython-0.3.0-cp314-cp314-manylinux_2_35_x86_64.whl) | 0.3.0 | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [usd-convert-cad](https://files.pythonhosted.org/packages/e3/9f/8683c0fe5a806d7d1788faa410ac183e94ad6b490554b02143db28bae3ed/usd_convert_cad-0.4.0-cp312-cp312-manylinux_2_35_x86_64.whl) | 0.4.0 | cp312 | 31 / 31 | `libpython3.12.so.1.0` |
| [usd-optimize](https://files.pythonhosted.org/packages/d4/8c/6a4c1bc3f849dbefb32a2f276edabbc6fb83a03e5bb8934ca73945b793c9/usd_optimize-1.4.0-cp312-cp312-manylinux_2_35_x86_64.whl) | 1.4.0 | cp312 | 1 / 1 | `libpython3.12.so.1.0` |
| [viame](https://files.pythonhosted.org/packages/dd/63/2c9af902ff4aca86f4530949bb7ae91912056d3e1b5c5e0c55cae2c708d0/viame-0.23.5-cp314-cp314-manylinux_2_35_x86_64.whl) | 0.23.5 | cp314 | 22 / 22 | `libpython3.14.so.1.0` |

### Affected wheels only for Python 3.10 or older: 43 projects

These releases ship nothing affected for a Python that still receives
updates.

| Project (inspected wheel) | Version | Python | Affected / extensions | Direct dependency |
| --- | --- | --- | ---: | --- |
| [cdcmis](https://files.pythonhosted.org/packages/e4/2f/76717cfad7bda5b7aef1417f1a3375c75ca4dae9ef72c1d55bab7bd10d0d/cdcmis-0.1.3-cp36-cp36m-manylinux1_x86_64.whl) | 0.1.3 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [cocopod](https://files.pythonhosted.org/packages/78/3d/ac145174373375e454c9a62502b40189e3d169ebfde6903f4d638c0e491c/cocopod-1.2.0-cp310-cp310-manylinux_2_17_x86_64.whl) | 1.2.0 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [cudagrad](https://files.pythonhosted.org/packages/1b/4d/5fd13253e9746e1c00bd601864f18793fa60f7515ea29260766d582bbb65/cudagrad-0.2.8-cp310-cp310-manylinux2014_x86_64.whl) | 0.2.8 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [dashinfer](https://files.pythonhosted.org/packages/a0/a6/bcf480d587be6eb6f56bb2f566b9e4bb025f5359f0ba4faac14f7997fa35/dashinfer-2.1.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) | 2.1.0 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [dg-nn-toolkit](https://files.pythonhosted.org/packages/d0/b8/314a1c4d3cc64e31251fd517672648c485b015a5879b3bbf07ef232eca83/dg_nn_toolkit-1.0.0-cp310-cp310-manylinux2014_x86_64.whl) | 1.0.0 | cp310 | 1 / 5 | `libpython3.10.so.1.0` |
| [diva-framework](https://files.pythonhosted.org/packages/c3/2e/923d4b3855cf48053877de4ff548a84fce393099e3f81b273e09391a165b/diva_framework-0.0.6-cp38-cp38-manylinux2014_x86_64.whl) | 0.0.6 | cp38 | 1 / 1 | `libpython3.8.so.1.0` |
| [dkube-cicd-controller](https://files.pythonhosted.org/packages/59/d8/82e919c1ff5fa5b1aea19dfc4f537fbf991b789d8248283e26fba800c67b/dkube_cicd_controller-1.6.2-cp37-cp37m-manylinux_2_5_x86_64.manylinux1_x86_64.whl) | 1.6.2 | cp37 | 16 / 16 | `libpython3.7m.so.1.0` |
| [dm-launchpad](https://files.pythonhosted.org/packages/fc/ae/c079515a39bcaeac18c650e27a79ef12e3f4f207a2f12da9af4ad13be0db/dm_launchpad-0.5.2-cp310-cp310-manylinux2014_x86_64.whl) | 0.5.2 | cp310 | 5 / 5 | `libpython3.10.so.1.0` |
| [forexconnect](https://files.pythonhosted.org/packages/7b/63/47526ae32f5659a4564fa355a16006156c65ca3d955216e63e0b93547f7a/forexconnect-1.6.43-cp37-cp37m-manylinux1_x86_64.whl) | 1.6.43 | cp37 | 1 / 1 | `libpython3.7m.so` |
| [fprintw](https://files.pythonhosted.org/packages/47/c8/30613465afbb969f9d67392bcf561a72b846963d9c0a22d4ea0e6521726f/fprintw-0.2.1-cp37-cp37m-manylinux1_x86_64.whl) | 0.2.1 | cp37 | 1 / 1 | `libpython3.7m.so.1.0` |
| [gcmapexplorer](https://files.pythonhosted.org/packages/24/e3/637d8e60212ca8b50a1e45d1ecc464ca108329eda1d9993402eb50a7318a/gcMapExplorer-1.0.30-cp36-cp36m-manylinux1_x86_64.whl) | 1.0.30 | cp36 | 5 / 5 | `libpython3.6m.so.1.0` |
| [hipppy](https://files.pythonhosted.org/packages/9a/9c/e120dbb62e29501f49ab2f88f95ee755eb6f01920a4abfa6a86cec203bfa/hipppy-0.1.0-cp36-cp36m-manylinux1_x86_64.whl) | 0.1.0 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [hoot](https://files.pythonhosted.org/packages/b5/ff/0c4e91006ac731d468092d85c5a46285ea1c62cf7e9be738d21de58b2889/hoot-0.2.64.14-cp37-cp37m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) | 0.2.64.14 | cp37 | 1 / 1 | `libpython3.7m.so.1.0` |
| [icraft](https://files.pythonhosted.org/packages/ac/83/4b3f2fbb39d326d025ac97e78e74d40be5effeeacf1f02858ba306458599/icraft-3.36.1-cp38-none-manylinux2014_x86_64.whl) | 3.36.1 | cp38 | 10 / 10 | `libpython3.8.so.1.0` |
| [kwiver](https://files.pythonhosted.org/packages/8a/e6/52c94774748ccd973ffc3feb45804c59eb4e16416ae7cec12d6c95da8942/kwiver-1.4.6-cp38-cp38-manylinux2014_x86_64.whl) | 1.4.6 | cp38 | 43 / 43 | `libpython3.8.so.1.0` |
| [lgraph](https://files.pythonhosted.org/packages/25/cb/647263d02fbc8801f170105de41d769f2a03dbdc3717250dedf5ac5cfe40/lgraph-0.1.3-cp36-cp36m-manylinux1_x86_64.whl) | 0.1.3 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [libmhcuda](https://files.pythonhosted.org/packages/80/ae/a27d62cfc3f3d2a08f72d25e5b1ab40261af33dd76d52008a6cbd5ef3917/libMHCUDA-2.3.0-cp310-cp310-manylinux_2_34_x86_64.whl) | 2.3.0 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [lxml-odidev](https://files.pythonhosted.org/packages/88/93/00fb3d490b8955e7899cc3b90e192b103dec7cbd41f4c5f1e0aec698fdde/lxml_odidev-4.5.0-cp37-cp37m-manylinux2014_aarch64.whl) | 4.5.0 | cp37 | 7 / 7 | `libpython3.7m.so.1.0` |
| [matlab-restfcnservice-client](https://files.pythonhosted.org/packages/5b/ea/18c438964846ddbcaedca17c8fc4fc1cd69a17a46221f55eb97f8f4ef1a7/matlab_restfcnservice_client-26.2.4-py3-none-manylinux_2_28_x86_64.whl) | 26.2.4 | py3 | 1 / 2 | `libpython3.10.so.1.0` |
| [mdw](https://files.pythonhosted.org/packages/43/0f/164384acc68a889edf7725b607b2f773374e8d97d0d4d171f263fc4c5212/mdw-1.1.1.4.2025.8.14.9.15-cp36-cp36m-manylinux1_x86_64.whl) | 1.1.1.4.2025.8.14.9.15 | cp36 | 52 / 54 | `libpython3.6m.so.1.0` |
| [mindscience-mindelec-ascend](https://files.pythonhosted.org/packages/41/9c/699b2e33e45a9272a7b2e647915663a8862904b3882a98bd7ef6a0410ca2/mindscience_mindelec_ascend-0.1.0-cp37-cp37m-manylinux1_x86_64.whl) | 0.1.0 | cp37 | 1 / 1 | `libpython3.7m.so.1.0` |
| [mindspore-federated](https://files.pythonhosted.org/packages/d4/a4/bfa76af377720c35b0c9658ec2d30fd4fcdc8e0e54443871e9e602961658/mindspore_federated-0.1.0-cp39-cp39-manylinux1_x86_64.whl) | 0.1.0 | cp39 | 1 / 1 | `libpython3.9.so.1.0` |
| [mindspore-serving](https://files.pythonhosted.org/packages/84/8c/0143bcb5fceeb2e7f9fc4c066e9101c2b929a3455a6f91a82a1fcb12aa3b/mindspore_serving-2.0.2-cp39-cp39-manylinux1_x86_64.whl) | 2.0.2 | cp39 | 1 / 1 | `libpython3.9.so.1.0` |
| [mix-deploy](https://files.pythonhosted.org/packages/33/92/71c374f55db03d5a4ed42ce9121b048cde0819b156c069f850de4403adde/mix_deploy-1.4.0-cp37-cp37m-manylinux1_x86_64.whl) | 1.4.0 | cp37 | 1 / 1 | `libpython3.7m.so.1.0` |
| [nimbusml](https://files.pythonhosted.org/packages/44/9c/e9f2c84a137a465ec4a29a1cc07fead9131c174ca4ef0c321bd7f1214324/nimbusml-1.8.0-cp38-none-manylinux1_x86_64.whl) | 1.8.0 | cp38 | 1 / 1 | `libpython3.8.so.1.0` |
| [numpy-demo](https://files.pythonhosted.org/packages/25/0e/53245c468b0cf40177fb032681c08ac9cb9527b9b784678ebe248936c4fe/numpy_demo-1.23.0-cp37-cp37m-manylinux2014_aarch64.whl) | 1.23.0 | cp37 | 18 / 18 | `libpython3.7m.so.1.0` |
| [packsim](https://files.pythonhosted.org/packages/49/83/7d7c3be6d87522def0580228ffffc42a8ea580597ebc31afe72d09b6af2f/packsim-0.1.0-cp38-cp38-manylinux_2_31_x86_64.whl) | 0.1.0 | cp38 | 5 / 5 | `libpython3.8.so.1.0` |
| [pandas-mpmkp](https://files.pythonhosted.org/packages/3b/f8/842264c8302ff079dae921e8bfb3c3879cf151976eb640e0c63558828080/pandas_mpmkp-1.0.9-cp37-cp37m-manylinux2014_aarch64.whl) | 1.0.9 | cp37 | 41 / 41 | `libpython3.7m.so.1.0` |
| [pim-dm](https://files.pythonhosted.org/packages/85/61/9716c489c719dc694c85fb36877eb9a0f02dfcaf3eaf4747012ab9654a28/pim_dm-1.4.1-cp36-cp36m-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) | 1.4.1 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [py2quickjs](https://files.pythonhosted.org/packages/34/a9/980b6b5e6c313525e776ac4990bf76af72d7d94d7ee15d82bc25395be5e2/py2quickjs-0.5.0-cp27-cp27mu-manylinux1_x86_64.whl) | 0.5.0 | cp27 | 1 / 1 | `libpython2.7.so.1.0` |
| [pycx4](https://files.pythonhosted.org/packages/ee/04/ac5a235e7ebed00c3e3c6ba37afde70e61c8bc522bdefdf269fbad846a85/pycx4-2.0.3-cp36-cp36m-manylinux2014_x86_64.whl) | 2.0.3 | cp36 | 2 / 2 | `libpython3.6m.so.1.0` |
| [pyds-ext](https://files.pythonhosted.org/packages/bd/4f/fc09975a44e6da326822bb52180c9c925a60d26b9b0ac5e210480f3c41ce/pyds_ext-2.0.0-cp38-cp38-manylinux2014_x86_64.whl) | 2.0.0 | cp38 | 1 / 1 | `libpython3.8.so.1.0` |
| [pyogmaneo](https://files.pythonhosted.org/packages/30/34/b4ac905cf0b0cc075f3c31b3d8de128307fed87bd089b76dac665d0a1603/pyogmaneo-1.0.3-cp38-cp38-manylinux1_x86_64.whl) | 1.0.3 | cp38 | 1 / 1 | `libpython3.8.so.1.0` |
| [pysuper](https://files.pythonhosted.org/packages/45/62/018df359821b9848553279fdf867d58ef4ec1328e2f755e08a2805c4f2ba/pysuper-0.2.91-cp36-cp36m-linux_armv7l.whl) | 0.2.91 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [pywht](https://files.pythonhosted.org/packages/aa/92/1ac93a7f9a41a2c101b5a4af5c0d9b6256fed881670b37c38492593bcc90/pywht-0.0.1-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.whl) | 0.0.1 | cp39 | 1 / 1 | `libpython3.9.so.1.0` |
| [rasqal](https://files.pythonhosted.org/packages/6f/73/3b8f68db69324534c7b42a5b09d6eb15b348a2ec4f2b3d945b818e0ee2ed/rasqal-0.1.7-cp310-cp310-manylinux_2_31_x86_64.whl) | 0.1.7 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [scenario](https://files.pythonhosted.org/packages/10/59/4096bf4dc9c8243070427bdfb0db6bcc7c80088421ca969a3f2c98f9c850/scenario-1.3.1-cp39-cp39-manylinux2014_x86_64.whl) | 1.3.1 | cp39 | 2 / 2 | `libpython3.9.so.1.0` |
| [scipy-mpmkp](https://files.pythonhosted.org/packages/f9/9f/7365377cb6c9c992b5099cf1e87de7a22b74cc0f47fb3d72b6e4ab48ba1b/scipy_mpmkp-1.4.1-cp37-cp37m-manylinux2014_aarch64.whl) | 1.4.1 | cp37 | 88 / 88 | `libpython3.7m.so.1.0` |
| [sptag](https://files.pythonhosted.org/packages/46/76/b3529cc4c7ff30210cedd8d620da1fda15d7dd47010e89e896754bd9d546/sptag-1.6.8-py39-none-manylinux1_x86_64.whl) | 1.6.8 | py39 | 2 / 2 | `libpython3.9.so.1.0` |
| [sys-prctl](https://files.pythonhosted.org/packages/86/45/6db88de68eddfe4c1023339d8525f7b4d88645e37d7d018ce388ef328b8a/sys_prctl-0.0.4-cp310-cp310-manylinux2014_x86_64.whl) | 0.0.4 | cp310 | 1 / 1 | `libpython3.10.so.1.0` |
| [taichi-gpu-nightly](https://files.pythonhosted.org/packages/7b/ce/34521c257f991c76c2f4c31c8e8b3779355ac4fddf8a02050fd06b9f3f21/taichi_gpu_nightly-0.0.59-cp36-cp36m-manylinux1_x86_64.whl) | 0.0.59 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [torchslide](https://files.pythonhosted.org/packages/4f/e2/02b3bf9abbfd281be5e48de030424209e9659a6afe983a8291d0d0c1c20e/torchslide-0.3.0-cp36-cp36m-manylinux1_x86_64.whl) | 0.3.0 | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
| [vdwlib](https://files.pythonhosted.org/packages/60/01/ce347caa38404ca94954becf002834ede5917af531e0e0a36edb550a6a7a/vdwlib-0.3.0-py38-py38m-manylinux1_x86_64.whl) | 0.3.0 | py38 | 4 / 4 | `libpython3.8.so.1.0` |

## Popularity sample: 5 more projects

The popularity sample found 8 affected projects. Three of them (`genicam`,
`isystem-connect` and `torch-xla`) are also in the tables above; these are
the other five. `cohere`, `pymeshlab` and `scanpy` were not among the
latest-release candidates (BigQuery lists no Linux wheel in their latest
release), so these rows come from the newest release that had one.
`jpype1` and `pybigwig` are affected in their piwheels ARM builds; the PyPI
x86-64 wheels inspected in the latest-release sample do not link libpython.

| Project (inspected wheel) | Version | Index | Python | Affected / extensions | Direct dependency |
| --- | --- | --- | --- | ---: | --- |
| [cohere](https://files.pythonhosted.org/packages/2b/3f/fd5e97b4dab010e537fb44adc7beb898d7597f85e3e7af0ad302d0092a06/cohere-2.1.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) | 2.1.0 | pypi | cp310 | 6 / 6 | `libpython3-dc2fd5ae.10.so.1.0`, `libpython3.6m.so.1.0`, `libpython3.7m.so.1.0`, `libpython3.8.so.1.0`, `libpython3.9.so.1.0` |
| [jpype1](https://archive1.piwheels.org/simple/jpype1/jpype1-1.6.0-cp311-cp311-linux_armv6l.whl) | 1.6.0 | piwheels | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [pybigwig](https://www.piwheels.org/simple/pybigwig/pybigwig-0.3.30-cp311-cp311-linux_armv6l.whl) | 0.3.30 | piwheels | cp311 | 1 / 1 | `libpython3.11.so.1.0` |
| [pymeshlab](https://files.pythonhosted.org/packages/79/c0/9b769a1acd7ce4405059820793c2f14129d9faba99b595ea35c8c9d8c57d/pymeshlab-2025.7.post1-cp314-cp314-manylinux_2_35_x86_64.whl) | 2025.7.post1 | pypi | cp314 | 1 / 1 | `libpython3.14.so.1.0` |
| [scanpy](https://files.pythonhosted.org/packages/f9/e6/cfabb71e9cee4b9cd426c461723814c4857cdc1ac5a93c0a18e3cd0b399c/scanpy-0.4.4-cp36-cp36m-manylinux1_x86_64.whl) | 0.4.4 | pypi | cp36 | 1 / 1 | `libpython3.6m.so.1.0` |
