# Azure

## AuthorizationFailed
Matches: `authorizationfailed`, `does not have authorization to perform action`

**Cause.** The signed-in user or service principal has no role assignment covering that action at that scope (resource, resource group or subscription).

**Fix.** Check the active account and its role assignments, then assign the narrowest built-in role at the right scope.

```sh
az account show
az role assignment list --assignee <object-id-or-upn> --all -o table
```

## Wrong subscription or not logged in
Matches: `subscriptionnotfound`, `please run 'az login'`, `no subscription found`

**Cause.** az is not logged in, or the active subscription is not the one holding the resource.

**Fix.** Log in and select the right subscription.

```sh
az login
az account list -o table
az account set --subscription <subscription-id>
```

## Resource provider not registered
Matches: `missingsubscriptionregistration`, `the subscription is not registered to use namespace`

**Cause.** The subscription has not registered the resource provider, for example Microsoft.ContainerService for AKS.

**Fix.** Register the provider and wait until it shows Registered.

```sh
az provider register --namespace <Microsoft.Provider>
az provider show --namespace <Microsoft.Provider> --query registrationState
```

## Quota exceeded for VM cores
Matches: `quotaexceeded`, `operation could not be completed as it results in exceeding approved`, `cores quota`

**Cause.** The subscription hit the regional vCPU quota for that VM family.

**Fix.** Check usage, then request a quota increase or use a different VM size or region.

```sh
az vm list-usage --location <location> -o table
```

## VM size not available (SkuNotAvailable)
Matches: `skunotavailable`, `the requested size for resource`, `is currently not available in location`

**Cause.** That VM size is not offered, or has no capacity, in the chosen region or zone, or it is restricted for the subscription.

**Fix.** List the sizes available in the region and pick another, or another zone.

```sh
az vm list-skus --location <location> --size Standard_D --output table
```

## AKS: kubelogin not found
Matches: `kubelogin`, `executable kubelogin not found`

**Cause.** AKS clusters with Entra ID integration need kubelogin to get tokens, and it is not installed.

**Fix.** Install it, fetch credentials, and convert the kubeconfig.

```sh
az aks install-cli
az aks get-credentials --resource-group <rg> --name <cluster>
kubelogin convert-kubeconfig -l azurecli
```
Tool: AKS

## AKS cannot pull from ACR (401 Unauthorized)
Matches: `azurecr.io`, `401 unauthorized`, `failed to authorize`

**Cause.** The cluster's kubelet identity has no AcrPull role on the registry.

**Fix.** Attach the registry to the cluster, then check connectivity.

```sh
az aks update --resource-group <rg> --name <cluster> --attach-acr <acr-name>
az aks check-acr --resource-group <rg> --name <cluster> --acr <acr-name>.azurecr.io
```
Tool: AKS

## Storage returns AuthorizationPermissionMismatch
Matches: `authorizationpermissionmismatch`, `this request is not authorized to perform this operation using this permission`

**Cause.** Owner or Contributor roles cover the control plane only. Reading or writing blobs with Entra ID needs a data-plane role.

**Fix.** Assign Storage Blob Data Reader or Contributor on the storage account.

```sh
az role assignment create --assignee <object-id> --role "Storage Blob Data Contributor" --scope <storage-account-resource-id>
```

## Key Vault access forbidden
Matches: `does not have secrets get permission`, `keyvault`, `forbiddenbyrbac`, `forbiddenbypolicy`

**Cause.** The identity has no access policy (access policy model) or RBAC role (RBAC model) for secrets on the vault, or the vault firewall blocks the caller.

**Fix.** Grant Key Vault Secrets User (RBAC) or a get and list access policy, and check the vault's network rules.

```sh
az keyvault show --name <vault> --query properties.enableRbacAuthorization
az role assignment create --assignee <object-id> --role "Key Vault Secrets User" --scope <vault-resource-id>
```

## Network security group blocks traffic
Matches: `network security group`, `nsg`, `securityrule`

**Cause.** An NSG on the subnet or NIC has no inbound allow rule for the port and source, or a higher-priority deny rule wins.

**Fix.** List the effective rules on the NIC and add an allow rule with a lower priority number than the deny.

```sh
az network nic list-effective-nsg --resource-group <rg> --name <nic>
```

## Another operation in progress
Matches: `anotheroperationinprogress`, `operation is in progress`

**Cause.** The resource is already being updated by another deployment, a portal change or an automation run.

**Fix.** Wait for the running operation to finish, then retry.

```sh
az resource show --ids <resource-id> --query properties.provisioningState
```
