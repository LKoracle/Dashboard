'use strict';
const base='/dashboard',content=document.querySelector('#content');
let navigationItems=[],loadError='',editingRoleVersion=null,editingProjectVersion=null,editingUserVersion=null,editingMetricVersion=null;
let user,items=[],canEdit=false,pending=null,listPages={menus:{page:1,size:10,total:0},roles:{page:1,size:10,total:0},projects:{page:1,size:10,total:0},users:{page:1,size:10,total:0},metrics:{page:1,size:10,total:0},funnels:{page:1,size:10,total:0},history:{page:1,size:20,total:0}};
let roles=[],rolesCanEdit=false,rolesCanCreate=false,roleMeta=null,editingRoleId=null;
let projects=[],projectsCanEdit=false,projectsCanCreate=false,editingProjectId=null;
let users=[],userRoleOptions=[],usersCanEdit=false,usersCanCreate=false,usersCanReset=false,editingUserId=null,roleDropdownOpen=false,selectedRoleIds=[];
let metrics=[],metricCategories=[],metricProjects=[],metricsCanEdit=false,metricsCanCreate=false,editingMetricId=null;
let metricSearchDraft={categoryId:'',projectId:'',name:''},metricSearchApplied={categoryId:'',projectId:'',name:''};
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const ic=(paths)=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
const ICONS={plus:ic('<path d="M12 5v14M5 12h14"/>'),edit:ic('<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),trash:ic('<path d="M3 6h18M8 6V4h8v2m-9 0v14a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6M10 11v6M14 11v6"/>'),pause:ic('<path d="M8 5v14M16 5v14"/>'),play:ic('<path d="m8 5 11 7-11 7Z" fill="currentColor" stroke-linejoin="round"/>'),up:ic('<path d="m18 15-6-6-6 6"/>'),down:ic('<path d="m6 9 6 6 6-6"/>'),key:ic('<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6M12 9v6m-2-4 2-2 2 2"/>')};
async function api(path,options={}){const response=await fetch(base+'/api'+path,{...options,headers:{'Content-Type':'application/json',...(user?{'X-CSRF-Token':user.csrf_token}:{}),...options.headers}});if(response.status===401){location.replace(base+'/login');throw Error('请重新登录');}const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'操作失败，请稍后重试');return data;}
let toastTimer;
function notify(message,position='bottom'){const n=document.querySelector('#toast');n.textContent=message;n.classList.toggle('toast-center',position==='center');n.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>n.hidden=true,3500);}
function enabled(row){const items=navigationItems;const seen=new Set();while(row){if(!row.is_enabled||seen.has(row.id))return false;seen.add(row.id);row=items.find(m=>m.id===row.parent_id);}return true;}
function currentPageKey(){if(location.pathname.endsWith('/maintain'))return 'maintain';if(location.pathname.endsWith('/settings/roles'))return 'roles';if(location.pathname.endsWith('/settings/projects'))return 'projects';if(location.pathname.endsWith('/settings/users'))return 'users';if(location.pathname.endsWith('/settings/metrics'))return 'metrics';if(location.pathname.endsWith('/settings/funnels'))return 'funnel';return 'menus';}
const SIDEBAR_ROUTES={project:'/settings/projects',menu:'/settings/menus',role:'/settings/roles',user:'/settings/users',metric:'/settings/metrics',funnel:'/settings/funnels'};
function navigation(){const items=navigationItems;const settings=location.pathname.includes('/settings/');const maintain=location.pathname.endsWith('/maintain');document.querySelector('#sidebar').hidden=!settings;content.classList.toggle('with-sidebar',settings);const savebar=document.querySelector('#savebar');if(savebar)savebar.hidden=!maintain;const TOP_ROUTES={'首页':'/','数据维护':'/maintain','设置管理':(items.filter(m=>SIDEBAR_ROUTES[m.code]&&enabled(m)).map(m=>SIDEBAR_ROUTES[m.code])[0]||'/settings/menus')};const top=document.querySelector('#topNav');top.replaceChildren();for(const name of ['首页','数据维护','设置管理']){const row=items.find(m=>m.name===name);const available=row&&enabled(row);const n=el(available?'a':'span',name,(name==='设置管理'&&settings||name==='首页'&&!settings&&!maintain||name==='数据维护'&&maintain)?'active':'');if(n.tagName==='A')n.href=base+TOP_ROUTES[name];else{n.classList.add('nav-disabled');n.title=available?'功能建设中':'菜单已停用';}top.append(n);}const nav=document.querySelector('#sideNav');nav.replaceChildren();const activeCode=({menus:'menu',roles:'role',users:'user',projects:'project',metrics:'metric'})[currentPageKey()]||currentPageKey();const permChildren=['menu','role','user'];const permActive=permChildren.includes(activeCode);for(const row of items.filter(m=>m.parent_id!==null)){const route=SIDEBAR_ROUTES[row.code];let linkable=!!route&&enabled(row);let cls='side-item'+((linkable&&row.code===activeCode)?' active':'');let href=base+route;if(row.code==='permission'){cls+=' perm-parent'+(permActive?' parent-active':'');linkable=enabled(row)&&permChildren.some(c=>SIDEBAR_ROUTES[c]&&items.some(m=>m.code===c&&enabled(m)));href=base+(permChildren.map(c=>items.find(m=>m.code===c&&enabled(m))).filter(Boolean).map(m=>SIDEBAR_ROUTES[m.code])[0]||'/settings/menus');}else if(row.parent_id===items.find(m=>m.code==='permission')?.id){cls+=' child';}const n=el(linkable?'a':'span',row.name,cls);if(linkable)n.href=href;else{n.classList.add('nav-disabled');n.title=!enabled(row)?'菜单已停用':'功能建设中';}nav.append(n);}}
function level(row){let result=1,seen=new Set();while(row.parent_id!==null&&!seen.has(row.id)){seen.add(row.id);row=items.find(m=>m.id===row.parent_id);if(!row)break;result++;}return result;}
function renderMenus(){content.replaceChildren();const crumb=el('p','设置管理 / 权限配置 / 菜单管理','breadcrumb');content.append(crumb);const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');titleRow.append(el('h1','菜单管理'),el('p','管理系统菜单层级、操作权限与启停状态。','subtitle'));heading.append(titleRow);content.append(heading);const card=el('section',undefined,'card');card.append(el('p',`共 ${items.length} 个菜单`,'table-count'));const wrap=el('div',undefined,'table-wrap'),table=el('table');table.setAttribute('aria-label','菜单管理');const head=el('thead'),tr=el('tr');['菜单','层级','上级菜单','操作权限','状态','操作'].forEach(t=>tr.append(el('th',t)));head.append(tr);table.append(head);const body=el('tbody');for(const row of pagedList('menus',items)){const r=el('tr');const name=el('td',row.name,'menu-name level-'+level(row));name.dataset.level=level(row);r.append(name,el('td',`${level(row)} 级`),el('td',items.find(m=>m.id===row.parent_id)?.name||'—'));const permissions=el('td'),chips=el('div',undefined,'chips');row.permissions.forEach(p=>chips.append(el('span',p,'chip')));permissions.append(chips);if(!row.permissions.length)permissions.textContent='—';r.append(permissions);const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);const action=el('td'),button=el('button',undefined,'icon-btn'+(row.is_enabled?'':' play-green'));button.type='button';button.innerHTML=row.is_enabled?ICONS.pause:ICONS.play;button.title=row.is_enabled?'停用':'启用';button.setAttribute('aria-label',(row.is_enabled?'停用':'启用')+'菜单'+row.name);button.disabled=!canEdit;button.addEventListener('click',()=>confirmMenuChange(row));action.append(button);r.append(action);body.append(r);}table.append(body);wrap.append(table);card.append(wrap);content.append(card);content.append(buildPager('menus','菜单'));}
function pagedList(key,arr){const p=listPages[key];p.total=arr.length;const count=Math.max(1,Math.ceil(p.total/p.size));p.page=Math.max(1,Math.min(p.page,count));return arr.slice((p.page-1)*p.size,p.page*p.size);}function goListPage(key,n){const p=listPages[key];const count=Math.max(1,Math.ceil(p.total/p.size));if(Number.isInteger(n)&&n>=1&&n<=count&&n!==p.page){p.page=n;render();}}function buildPager(key,label){const p=listPages[key];const count=Math.max(1,Math.ceil(p.total/p.size));const pages=[];for(let n=1;n<=count;n++){if(count<=7||n===1||n===count||Math.abs(n-p.page)<=1)pages.push(n);else if(pages[pages.length-1]!=='…')pages.push('…');}const pager=el('nav',undefined,'metric-pagination');pager.setAttribute('aria-label',label+'列表分页');const select=el('select');select.setAttribute('aria-label','每页显示条数');[10,20,50].forEach(n=>{const option=el('option',n+' 条 / 页');option.value=n;option.selected=n===p.size;select.append(option);});select.addEventListener('change',()=>{const size=Number(select.value);if([10,20,50].includes(size)){p.size=size;p.page=1;render();}});pager.append(select);const prev=el('button','上一页','secondary');prev.type='button';prev.setAttribute('aria-label','上一页');prev.disabled=p.page===1;prev.addEventListener('click',()=>goListPage(key,p.page-1));pager.append(prev);for(const n of pages){if(n==='…'){const dots=el('span','…');dots.setAttribute('aria-hidden','true');pager.append(dots);}else{const b=el('button',String(n),n===p.page?'primary':'secondary');b.type='button';b.setAttribute('aria-label','第 '+n+' 页');if(n===p.page)b.setAttribute('aria-current','page');else b.addEventListener('click',()=>goListPage(key,n));pager.append(b);}}const next=el('button','下一页','secondary');next.type='button';next.setAttribute('aria-label','下一页');next.disabled=p.page===count;next.addEventListener('click',()=>goListPage(key,p.page+1));pager.append(next);return pager;}function renderRoles(){content.replaceChildren();const crumb=el('p','设置管理 / 权限配置 / 角色管理','breadcrumb');content.append(crumb);const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');titleRow.append(el('h1','角色管理'),el('p','管理菜单与操作权限、角色及用户。','subtitle'));heading.append(titleRow);content.append(heading);const card=el('section',undefined,'card');const toolbar=el('div',undefined,'toolbar');toolbar.append(el('span',`共 ${roles.length} 个角色`,'count'),el('span',undefined,'spacer'));const addBtn=el('button',undefined,'primary');addBtn.innerHTML=ICONS.plus+'新增角色';addBtn.disabled=!rolesCanCreate;addBtn.addEventListener('click',()=>openRoleForm(null));toolbar.append(addBtn);card.append(toolbar);const wrap=el('div',undefined,'table-wrap'),table=el('table');table.setAttribute('aria-label','角色管理');const head=el('thead'),tr=el('tr');['角色名称','可访问菜单','操作权限','项目范围','状态','操作'].forEach(t=>tr.append(el('th',t)));head.append(tr);table.append(head);const body=el('tbody');if(!roles.length){const empty=el('tr'),td=el('td','暂无角色，点击右上角「新增角色」创建。');td.colSpan=6;td.style.textAlign='center';td.style.color='#7c8ba1';td.style.padding='40px';empty.append(td);body.append(empty);}for(const row of pagedList('roles',roles)){const r=el('tr');const nameTd=el('td',undefined,'menu-name');nameTd.append(el('strong',row.name));r.append(nameTd);const menuTd=el('td'),menuChips=el('div',undefined,'chips');row.menus.forEach(m=>menuChips.append(el('span',m,'chip')));menuTd.append(menuChips);if(!row.menus.length)menuTd.textContent='—';r.append(menuTd);r.append(el('td',`${row.permission_count} 项`));r.append(el('td',`${row.project_count} 个项目`));const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);const action=el('td'),actBox=el('div',undefined,'order-btns');const isSuper=row.code==='super_admin';const editBtn=el('button',undefined,'icon-btn');editBtn.innerHTML=ICONS.edit;editBtn.title='编辑';editBtn.disabled=!rolesCanEdit||isSuper;editBtn.addEventListener('click',()=>openRoleForm(row));const toggleBtn=el('button',undefined,'icon-btn');toggleBtn.innerHTML=row.is_enabled?ICONS.pause:ICONS.play;toggleBtn.title=row.is_enabled?'停用':'启用';toggleBtn.disabled=!rolesCanEdit||isSuper;toggleBtn.addEventListener('click',()=>confirmRoleChange(row));const delBtn=el('button',undefined,'icon-btn');delBtn.innerHTML=ICONS.trash;delBtn.title='删除';delBtn.disabled=!rolesCanEdit||isSuper;delBtn.addEventListener('click',()=>confirmRoleDelete(row));if(isSuper){actBox.append(el('span','内置','chip'));}else{actBox.append(editBtn,toggleBtn,delBtn);}action.append(actBox);r.append(action);body.append(r);}table.append(body);wrap.append(table);card.append(wrap);content.append(card);content.append(buildPager('roles','角色'));}
function renderUsers(){content.replaceChildren();const crumb=el('p','设置管理 / 权限配置 / 用户管理','breadcrumb');content.append(crumb);const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');titleRow.append(el('h1','用户管理'),el('p','管理菜单与操作权限、角色及用户。','subtitle'));heading.append(titleRow);content.append(heading);const card=el('section',undefined,'card');const toolbar=el('div',undefined,'toolbar');toolbar.append(el('span',`共 ${users.length} 个用户`,'count'),el('span',undefined,'spacer'));const addBtn=el('button',undefined,'primary');addBtn.innerHTML=ICONS.plus+'新增用户';addBtn.disabled=!usersCanCreate;addBtn.addEventListener('click',()=>openUserForm(null));toolbar.append(addBtn);card.append(toolbar);const wrap=el('div',undefined,'table-wrap'),table=el('table');table.setAttribute('aria-label','用户管理');const head=el('thead'),tr=el('tr');['用户ID','用户名称','角色','状态','操作'].forEach(t=>tr.append(el('th',t)));head.append(tr);table.append(head);const body=el('tbody');if(!users.length){const empty=el('tr'),td=el('td','暂无用户，点击右上角「新增用户」创建。');td.colSpan=5;td.style.textAlign='center';td.style.color='#7c8ba1';td.style.padding='40px';empty.append(td);body.append(empty);}for(const row of pagedList('users',users)){const r=el('tr');r.append(el('td',row.login_id));const nameTd=el('td',undefined,'menu-name');nameTd.append(el('strong',row.display_name));r.append(nameTd);const roleTd=el('td'),roleChips=el('div',undefined,'chips');row.roles.forEach(x=>roleChips.append(el('span',x.name,'chip blue')));roleTd.append(roleChips);if(!row.roles.length)roleTd.textContent='未分配';r.append(roleTd);const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);const action=el('td'),actBox=el('div',undefined,'order-btns');const editBtn=el('button',undefined,'icon-btn');editBtn.innerHTML=ICONS.edit;editBtn.title='编辑';editBtn.setAttribute('aria-label','编辑用户'+row.display_name);editBtn.disabled=!usersCanEdit;editBtn.addEventListener('click',()=>openUserForm(row));const toggleBtn=el('button',undefined,'icon-btn'+(row.is_enabled?'':' play-green'));toggleBtn.innerHTML=row.is_enabled?ICONS.pause:ICONS.play;toggleBtn.title=row.is_enabled?'停用':'启用';toggleBtn.setAttribute('aria-label',(row.is_enabled?'停用':'启用')+'用户'+row.display_name);toggleBtn.disabled=!usersCanEdit;toggleBtn.addEventListener('click',()=>confirmUserChange(row));const resetBtn=el('button',undefined,'icon-btn');resetBtn.innerHTML=ICONS.key;resetBtn.title='重置密码';resetBtn.setAttribute('aria-label','重置用户'+row.display_name+'的密码');resetBtn.disabled=!usersCanReset;resetBtn.addEventListener('click',()=>confirmUserReset(row));actBox.append(editBtn,toggleBtn,resetBtn);action.append(actBox);r.append(action);body.append(r);}table.append(body);wrap.append(table);card.append(wrap);content.append(card);content.append(buildPager('users','用户'));}
function filteredMetrics(){const name=metricSearchApplied.name.trim().toLocaleLowerCase();return metrics.filter(m=>(!metricSearchApplied.categoryId||String(m.category_id)===metricSearchApplied.categoryId)&&(!metricSearchApplied.projectId||String(m.project_id)===metricSearchApplied.projectId)&&(!name||m.name.toLocaleLowerCase().includes(name)));}
function renderMetricSearch(){
 const form=el('form',undefined,'metric-search');form.setAttribute('aria-label','指标查询');
 const categoryField=el('div',undefined,'metric-search-field');const categoryLabel=el('label','指标类型');categoryLabel.htmlFor='metricSearchCategory';
 const category=el('select');category.id='metricSearchCategory';category.name='category_id';
 const all=el('option','全部类型');all.value='';category.append(all);
 for(const c of metricCategories){const option=el('option',c.name);option.value=String(c.id);category.append(option);}
 category.value=metricSearchDraft.categoryId;category.addEventListener('change',()=>{metricSearchDraft.categoryId=category.value;});
 categoryField.append(categoryLabel,category);
 const projectField=el('div',undefined,'metric-search-field');const projectLabel=el('label','适用项目');projectLabel.htmlFor='metricSearchProject';
 const project=el('select');project.id='metricSearchProject';project.name='project_id';
 const allProjects=el('option','全部项目');allProjects.value='';project.append(allProjects);
 for(const p of metricProjects){const option=el('option',p.name);option.value=String(p.id);project.append(option);}
 project.value=metricSearchDraft.projectId;project.addEventListener('change',()=>{metricSearchDraft.projectId=project.value;});projectField.append(projectLabel,project);
 const nameField=el('div',undefined,'metric-search-field metric-search-name');const nameLabel=el('label','指标名称');nameLabel.htmlFor='metricSearchName';
 const name=el('input');name.id='metricSearchName';name.name='name';name.type='text';name.placeholder='请输入指标名称，支持模糊查询';name.maxLength=100;name.value=metricSearchDraft.name;
 name.addEventListener('input',()=>{metricSearchDraft.name=name.value;});nameField.append(nameLabel,name);
 const actions=el('div',undefined,'metric-search-actions');const query=el('button','查询','primary');query.type='submit';const reset=el('button','重置','secondary');reset.type='button';
 form.addEventListener('submit',e=>{e.preventDefault();metricSearchDraft={categoryId:category.value,projectId:project.value,name:name.value.trim()};metricSearchApplied={...metricSearchDraft};listPages.metrics.page=1;render();});
 reset.addEventListener('click',()=>{metricSearchDraft={categoryId:'',projectId:'',name:''};metricSearchApplied={categoryId:'',projectId:'',name:''};listPages.metrics.page=1;render();});
 actions.append(query,reset);form.append(categoryField,projectField,nameField,actions);return form;
}
function renderMetrics(){const matched=filteredMetrics();content.replaceChildren();const crumb=el('p','设置管理 / 指标管理','breadcrumb');content.append(crumb);const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');titleRow.append(el('h1','指标管理'),el('p','维护指标名称与统计口径，配置各项目适用指标与首页主指标。','subtitle'));heading.append(titleRow);const addBtn=el('button',undefined,'primary');addBtn.innerHTML=ICONS.plus+'新增指标';addBtn.disabled=!metricsCanCreate;addBtn.addEventListener('click',()=>openMetricForm(null));heading.append(addBtn);content.append(heading);const card=el('section',undefined,'card');card.append(renderMetricSearch());const count=el('p',`共 ${matched.length} 个指标`,'metric-search-count');count.setAttribute('role','status');card.append(count);const wrap=el('div',undefined,'table-wrap'),table=el('table');table.classList.add('metric-config-table');table.setAttribute('aria-label','指标管理');const head=el('thead'),tr=el('tr');[['类型',90],['指标编码',96],['指标名称',null],['英文缩写',null],['单位',70],['小数位数',85],['适用项目',214],['关键指标',78],['展示趋势',78],['状态',76],['操作',90]].forEach(([t,w])=>{const th=el('th',t);if(w)th.style.width=w+'px';tr.append(th);});head.append(tr);table.append(head);const body=el('tbody');if(!matched.length){const empty=el('tr');const tdEmpty=el('td',metrics.length?'未找到符合条件的指标，请调整查询条件。':'暂无指标，点击右上角「新增指标」创建。');tdEmpty.colSpan=11;tdEmpty.style.textAlign='center';tdEmpty.style.color='#7c8ba1';tdEmpty.style.padding='40px';empty.append(tdEmpty);body.append(empty);}for(const row of pagedList('metrics',matched)){const r=el('tr');const dimTd=el('td');dimTd.append(el('span',row.category_name,'tag'));r.append(dimTd);const codeTd=el('td',row.code);codeTd.style.whiteSpace='nowrap';r.append(codeTd);const nameTd=el('td');nameTd.append(el('strong',row.name));if(!row.definition)nameTd.append(el('div','口径待确认','muted name-pending'));r.append(nameTd);const enTd=el('td',row.english_name||'—');enTd.style.minWidth='170px';enTd.style.overflowWrap='anywhere';r.append(enTd);r.append(el('td',row.unit));r.append(el('td',String(row.decimal_places)));r.append(el('td',row.project_name));const keyTd=el('td');const keySw=el('button',undefined,'switch'+(row.is_key_metric?' on':''));keySw.type='button';keySw.setAttribute('role','switch');keySw.setAttribute('aria-checked',String(row.is_key_metric));keySw.title='关键指标';keySw.setAttribute('aria-label','关键指标：'+row.name);keySw.disabled=!metricsCanEdit||row.can_edit===false;keySw.addEventListener('click',()=>toggleMetricSwitch(row,'is_key_metric'));keyTd.append(keySw);r.append(keyTd);const trendTd=el('td');const trendSw=el('button',undefined,'switch'+(row.show_trend?' on':''));trendSw.type='button';trendSw.setAttribute('role','switch');trendSw.setAttribute('aria-checked',String(row.show_trend));trendSw.title='展示趋势';trendSw.setAttribute('aria-label','展示趋势：'+row.name);trendSw.disabled=!metricsCanEdit||row.can_edit===false;trendSw.addEventListener('click',()=>toggleMetricSwitch(row,'show_trend'));trendTd.append(trendSw);r.append(trendTd);const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);const action=el('td'),actBox=el('div',undefined,'order-btns');const editBtn=el('button',undefined,'icon-btn');editBtn.innerHTML=ICONS.edit;editBtn.title='编辑';editBtn.setAttribute('aria-label','编辑指标'+row.name);editBtn.disabled=!metricsCanEdit||row.can_edit===false;editBtn.addEventListener('click',()=>openMetricForm(row));const toggleBtn=el('button',undefined,'icon-btn'+(row.is_enabled?'':' play-green'));toggleBtn.innerHTML=row.is_enabled?ICONS.pause:ICONS.play;toggleBtn.title=row.is_enabled?'停用':'启用';toggleBtn.setAttribute('aria-label',(row.is_enabled?'停用':'启用')+'指标'+row.name);toggleBtn.disabled=!metricsCanEdit||row.can_edit===false;toggleBtn.addEventListener('click',()=>confirmMetricChange(row));actBox.append(editBtn,toggleBtn);action.append(actBox);r.append(action);body.append(r);}table.append(body);wrap.append(table);card.append(wrap);content.append(card);content.append(buildPager('metrics','指标'));}
function confirmMetricChange(row){pending=row;const action=row.is_enabled?'停用':'启用';document.querySelector('#confirmTitle').textContent=action+'指标';document.querySelector('#confirmText').textContent=`确认${action}“${row.name}”？`+(row.is_enabled?'停用后该指标将不再参与首页展示与数据统计。':'该指标将恢复可用。');document.querySelector('#confirmChange').textContent='确认'+action;document.querySelector('#confirmDialog').showModal();}
async function toggleMetricSwitch(row,field){if(!metricsCanEdit)return;try{await api('/metrics/'+row.id,{method:'PATCH',body:JSON.stringify({[field]:!row[field],row_version:row.row_version})});if(field==='show_trend')notify(row.show_trend?'已设置不展示趋势':'已设置展示趋势');else if(field==='is_key_metric')notify(row.is_key_metric?'已取消关键指标':'已设为关键指标');await load();}catch(ex){notify(ex.message);await load();}}
function confirmUserChange(row){pending=row;const action=row.is_enabled?'停用':'启用';document.querySelector('#confirmTitle').textContent=action+'用户';document.querySelector('#confirmText').textContent=`确认${action}“${row.display_name}”？`+(row.is_enabled?'停用后该用户将无法登录，现有登录状态立即失效。':'该用户将恢复登录。');document.querySelector('#confirmChange').textContent='确认'+action;document.querySelector('#confirmDialog').showModal();}
function confirmUserReset(row){pending=row;document.querySelector('#confirmTitle').textContent='重置密码';document.querySelector('#confirmText').textContent=`确认将用户「${row.display_name}」（${row.login_id}）的密码恢复为系统初始密码？`;document.querySelector('#confirmChange').textContent='确认重置';document.querySelector('#confirmDialog').showModal();}
function confirmMenuChange(row){pending=row;const action=row.is_enabled?'停用':'启用';document.querySelector('#confirmTitle').textContent=action+'菜单';document.querySelector('#confirmText').textContent=`确认${action}“${row.name}”？`+(row.is_enabled?'普通用户将无法通过该菜单及其下级菜单访问对应页面。':'对应菜单将恢复可用。');document.querySelector('#confirmChange').textContent='确认'+action;document.querySelector('#confirmDialog').showModal();}
function confirmRoleChange(row){pending=row;const action=row.is_enabled?'停用':'启用';document.querySelector('#confirmTitle').textContent=action+'角色';document.querySelector('#confirmText').textContent=`确认${action}“${row.name}”？`+(row.is_enabled?'该角色将不再参与授权，相关用户相应权限失效。':'该角色将恢复可用。');document.querySelector('#confirmChange').textContent='确认'+action;document.querySelector('#confirmDialog').showModal();}
function confirmRoleDelete(row){pending=row;document.querySelector('#confirmTitle').textContent='删除角色';document.querySelector('#confirmText').textContent=`确认删除角色“${row.name}”？此操作不可撤销。`;document.querySelector('#confirmChange').textContent='确认删除';document.querySelector('#confirmDialog').showModal();}
document.querySelector('#cancelChange').addEventListener('click',()=>document.querySelector('#confirmDialog').close());
document.querySelector('#confirmChange').addEventListener('click',async e=>{const row=pending;if(!row)return;const btn=e.currentTarget;const key=currentPageKey();const path=key==='roles'?'/roles/':(key==='projects'?'/projects/':(key==='users'?'/users/':(key==='metrics'?'/metrics/':(key==='funnel'?'/funnels/':'/menus/'))));const title=document.querySelector('#confirmTitle').textContent;const isDelete=title==='删除角色';const isReset=title==='重置密码';btn.disabled=true;try{if(isDelete){await api(path+row.id,{method:'DELETE'});notify('角色已删除');}else if(isReset){await api(path+row.id+'/reset-password',{method:'POST'});notify('密码已重置为系统初始密码');}else if(key==='funnel'){await api('/funnels/'+row.id+'/enabled',{method:'PATCH',body:JSON.stringify({enabled:!row.is_enabled,row_version:row.row_version})});notify('漏斗状态已更新');}else{await api(path+row.id,{method:'PATCH',body:JSON.stringify({is_enabled:!row.is_enabled,row_version:row.row_version})});notify(key==='projects'?'项目状态已更新':(key==='roles'?'角色状态已更新':(key==='users'?'用户状态已更新':(key==='metrics'?'指标状态已更新':'菜单状态已更新'))));}document.querySelector('#confirmDialog').close();}catch(ex){document.querySelector('#confirmDialog').close();notify(ex.message);}finally{btn.disabled=false;load().catch(ex=>notify(ex.message));}});
function render(){for(const id of ['confirmDialog','roleDialog','projectDialog','userDialog','metricDialog']){const d=document.querySelector('#'+id);if(d&&d.open)d.close();}navigation();if(loadError){content.replaceChildren(el('p',loadError,'form-error'));const retry=el('button','重新加载','secondary');retry.onclick=()=>load();content.append(retry);return;}const key=currentPageKey();if(key==='roles'){renderRoles();}else if(key==='projects'){renderProjects();}else if(key==='users'){renderUsers();}else if(key==='metrics'){renderMetrics();}else if(key==='maintain'){renderMaintain();}else if(key==='funnel'){funnelEdit?renderFunnelEditor():renderFunnels();}else{renderMenus();}}
function renderProjects(){content.replaceChildren();const crumb=el('p','设置管理 / 项目管理','breadcrumb');content.append(crumb);const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');titleRow.append(el('h1','项目管理'),el('p','维护系统中的项目、启停状态、首页展示顺序与功能清单。','subtitle'));heading.append(titleRow);content.append(heading);const card=el('section',undefined,'card');const toolbar=el('div',undefined,'toolbar');toolbar.append(el('span',`共 ${projects.length} 个项目`,'count'),el('span',undefined,'spacer'));const addBtn=el('button',undefined,'primary');addBtn.innerHTML=ICONS.plus+'新增项目';addBtn.disabled=!projectsCanCreate;addBtn.addEventListener('click',()=>openProjectForm(null));toolbar.append(addBtn);card.append(toolbar);const wrap=el('div',undefined,'table-wrap'),table=el('table');table.setAttribute('aria-label','项目管理');const head=el('thead'),tr=el('tr');['首页顺序','项目名称','功能清单','状态','操作'].forEach(t=>tr.append(el('th',t)));head.append(tr);table.append(head);const body=el('tbody');if(!projects.length){const empty=el('tr'),td=el('td','暂无项目，点击右上角「新增项目」创建。');td.colSpan=5;td.style.textAlign='center';td.style.color='#7c8ba1';td.style.padding='40px';empty.append(td);body.append(empty);}for(const row of pagedList('projects',projects)){const r=el('tr');const orderTd=el('td'),orderBox=el('div',undefined,'order-btns');orderBox.append(el('span',String(row.display_order),'order-num'));const upBtn=el('button',undefined,'icon-btn');upBtn.innerHTML=ICONS.up;upBtn.title='上移';upBtn.disabled=!projectsCanEdit;upBtn.addEventListener('click',()=>moveProject(row,'up'));const downBtn=el('button',undefined,'icon-btn');downBtn.innerHTML=ICONS.down;downBtn.title='下移';downBtn.disabled=!projectsCanEdit;downBtn.addEventListener('click',()=>moveProject(row,'down'));orderBox.append(upBtn,downBtn);orderTd.append(orderBox);r.append(orderTd);const nameTd=el('td',undefined,'menu-name');nameTd.append(el('strong',row.name));r.append(nameTd);const fnTd=el('td'),fnList=el('div',undefined,'func-list');row.features.forEach(f=>fnList.append(el('span',f,'fchip')));fnTd.append(fnList);if(!row.features.length){fnTd.textContent='—';fnTd.style.color='#94a3b8';fnTd.style.fontSize='12px';}r.append(fnTd);const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);const action=el('td'),actBox=el('div',undefined,'order-btns');const editBtn=el('button',undefined,'icon-btn');editBtn.innerHTML=ICONS.edit;editBtn.title='编辑';editBtn.disabled=!projectsCanEdit||row.can_edit===false;editBtn.addEventListener('click',()=>openProjectForm(row));const toggleBtn=el('button',undefined,'icon-btn');if(row.is_enabled){toggleBtn.innerHTML=ICONS.pause;toggleBtn.title='停用';}else{toggleBtn.innerHTML=ICONS.play;toggleBtn.title='启用';toggleBtn.classList.add('play-green');}toggleBtn.disabled=!projectsCanEdit||row.can_edit===false;toggleBtn.addEventListener('click',()=>confirmProjectToggle(row));actBox.append(editBtn,toggleBtn);action.append(actBox);r.append(action);body.append(r);}table.append(body);wrap.append(table);card.append(wrap);content.append(card);content.append(buildPager('projects','项目'));}
function confirmProjectToggle(row){pending=row;const action=row.is_enabled?'停用':'启用';document.querySelector('#confirmTitle').textContent=action+'项目';document.querySelector('#confirmText').textContent=`确认${action}“${row.name}”？`+(row.is_enabled?'停用后该项目将从首页展示中移除，相关指标与功能暂不可用。':'该项目将恢复可用。');document.querySelector('#confirmChange').textContent='确认'+action;document.querySelector('#confirmDialog').showModal();}
async function moveProject(row,dir){if(!projectsCanEdit)return;try{await api(`/projects/${row.id}/move`,{method:'PATCH',body:JSON.stringify({direction:dir,row_version:row.row_version})});await load();}catch(ex){notify(ex.message);await load();}}
async function openProjectForm(row){editingProjectId=row?row.id:null;editingProjectVersion=row?.row_version??null;const dialog=document.querySelector('#projectDialog');document.querySelector('#projectFormTitle').textContent=row?'编辑项目':'新增项目';document.querySelector('#projectName').value=row?row.name:'';document.querySelector('#projectNameErr').hidden=true;let features=[];let enabled=true;if(row){const detail=await api('/projects/'+row.id);document.querySelector('#projectName').value=detail.name;features=detail.features;enabled=detail.is_enabled;editingProjectVersion=detail.row_version;}setProjectSwitch(enabled);renderProjectFeatures(features);document.querySelector('#projectFnInput').value='';dialog.showModal();}
function renderProjectFeatures(features){const box=document.querySelector('#projectFnList');box.dataset.features=JSON.stringify(features);box.replaceChildren();if(!features.length){box.append(el('span','暂未添加功能','fchip empty'));return;}features.forEach((f,i)=>{const chip=el('span',undefined,'fchip');chip.append(document.createTextNode(f));const btn=el('button','×');btn.type='button';btn.addEventListener('click',()=>{features.splice(i,1);renderProjectFeatures(features);});chip.append(btn);box.append(chip);});box.dataset.features=JSON.stringify(features);}
function currentProjectFeatures(){try{return JSON.parse(document.querySelector('#projectFnList').dataset.features||'[]');}catch{return [];}}
function addProjectFeature(){const input=document.querySelector('#projectFnInput');const name=input.value.trim();if(!name)return;const features=currentProjectFeatures().filter(f=>f!=='暂未添加功能');features.push(name);renderProjectFeatures(features);input.value='';input.focus();}
function setProjectSwitch(on){const sw=document.querySelector('#projectEnabled'),txt=document.querySelector('#projectEnabledText');sw.classList.toggle('on',on);sw.setAttribute('aria-checked',String(on));txt.textContent=on?'启用':'停用';}
function collectProjectForm(){const name=document.querySelector('#projectName').value.trim();const is_enabled=document.querySelector('#projectEnabled').getAttribute('aria-checked')==='true';const features=currentProjectFeatures().filter(f=>f!=='暂未添加功能');return {name,is_enabled,features,row_version:editingProjectVersion};}
async function openRoleForm(row){if(!roleMeta){try{roleMeta=await api('/roles/meta');}catch(ex){notify(ex.message);return;}}editingRoleId=row?row.id:null;editingRoleVersion=row?.row_version??null;const dialog=document.querySelector('#roleDialog');document.querySelector('#roleFormTitle').textContent=row?'编辑角色':'新增角色';document.querySelector('#roleName').value=row?row.name:'';document.querySelector('#roleNameErr').hidden=true;let roleEnabled=true;let permIds=new Set(),projIds=new Set();if(row){const detail=await api('/roles/'+row.id);document.querySelector('#roleName').value=detail.name;editingRoleVersion=detail.row_version;permIds=new Set(detail.permission_ids);projIds=new Set(detail.project_ids);roleEnabled=detail.is_enabled;}setRoleSwitch(roleEnabled);const permBox=document.querySelector('#rolePermTree');permBox.replaceChildren();const menus=roleMeta.menus;const buildBranch=parentId=>{const children=menus.filter(m=>(m.parent_id??null)===parentId);return children.map(m=>{const branch=el('section',undefined,'role-branch');branch.append(el('div',m.name,'role-menu-name'));if(m.permissions.length){const acts=el('div',undefined,'role-tree-actions');for(const p of m.permissions){const pl=el('label',undefined,'role-tree-label');const pc=el('input');pc.type='checkbox';pc.dataset.permId=p.id;pc.checked=permIds.has(p.id);pl.append(pc,el('span',p.name));acts.append(pl);}branch.append(acts);}const kids=menus.some(x=>(x.parent_id??null)===m.id);if(kids){const kidBox=el('div',undefined,'role-children');kidBox.append(...buildBranch(m.id));branch.append(kidBox);}return branch;});};permBox.append(...buildBranch(null));const projBox=document.querySelector('#roleProjects');projBox.replaceChildren();for(const p of roleMeta.projects){const pl=el('label',undefined,'check-item'+(projIds.has(p.id)?' on':''));const pc=el('input');pc.type='checkbox';pc.value=p.id;pc.checked=projIds.has(p.id);pc.addEventListener('change',()=>{pl.classList.toggle('on',pc.checked);});pl.append(pc,el('span',p.name));projBox.append(pl);}dialog.showModal();}
function collectRoleForm(){const permIds=Array.from(document.querySelectorAll('#rolePermTree input[data-perm-id]:checked')).map(x=>Number(x.dataset.permId));const projIds=Array.from(document.querySelectorAll('#roleProjects input:checked')).map(x=>Number(x.value));const name=document.querySelector('#roleName').value.trim();const is_enabled=document.querySelector('#roleEnabled').getAttribute('aria-checked')==='true';return {name,permission_ids:permIds,project_ids:projIds,is_enabled,row_version:editingRoleVersion};}
function setRoleSwitch(on){const sw=document.querySelector('#roleEnabled'),txt=document.querySelector('#roleEnabledText');sw.classList.toggle('on',on);sw.setAttribute('aria-checked',String(on));txt.textContent=on?'启用':'停用';}
document.querySelector('#roleEnabled').addEventListener('click',()=>{const sw=document.querySelector('#roleEnabled');setRoleSwitch(sw.getAttribute('aria-checked')!=='true');});
document.querySelector('#roleCancel').addEventListener('click',()=>document.querySelector('#roleDialog').close());
document.querySelector('#roleClose').addEventListener('click',()=>document.querySelector('#roleDialog').close());
document.querySelector('#roleSave').addEventListener('click',async e=>{const data=collectRoleForm();if(!data.name){document.querySelector('#roleNameErr').hidden=false;document.querySelector('#roleName').focus();return;}const btn=e.currentTarget;btn.disabled=true;let saved=false;try{if(editingRoleId){await api('/roles/'+editingRoleId,{method:'PUT',body:JSON.stringify(data)});notify('角色已保存');}else{await api('/roles',{method:'POST',body:JSON.stringify(data)});notify('角色已创建');}saved=true;document.querySelector('#roleDialog').close();}catch(ex){notify(ex.message);}finally{btn.disabled=false;if(saved)load().catch(ex=>notify(ex.message));}});
async function load(){loadError='';try{
 const nav=await api('/navigation');navigationItems=nav.items;
 const key=currentPageKey();
 if(key==='maintain'){await loadMaintain();render();return;}
 if(key==='menus'){const d=await api('/menus');items=d.items;canEdit=d.can_edit;}
 else if(key==='roles'){const d=await api('/roles');roles=d.items;rolesCanEdit=d.can_edit;rolesCanCreate=d.can_create;}
 else if(key==='projects'){const d=await api('/projects');projects=d.items;projectsCanEdit=d.can_edit;projectsCanCreate=d.can_create;}
 else if(key==='users'){const d=await api('/users');users=d.items;userRoleOptions=d.roles;usersCanEdit=d.can_edit;usersCanCreate=d.can_create;usersCanReset=d.can_reset;}
 else if(key==='metrics'){const d=await api('/metrics');metrics=d.items;metricCategories=d.categories;metricProjects=d.projects;metricsCanEdit=d.can_edit;metricsCanCreate=d.can_create;}
 else if(key==='funnel'){const d=await api('/funnels');funnels=d.items;funnelOptions=d.options;funnelProjects=d.projects;funnelsCanCreate=d.can_create;funnelsCanEdit=d.can_edit;}
 }catch(ex){loadError=ex.message;}render();}
(async()=>{try{user=await api('/me');document.querySelector('#accountName').textContent=user.display_name;document.querySelector('#accountName').hidden=user.login_id==='admin';await load();}catch(ex){content.replaceChildren(el('p',ex.message,'form-error'));}})();
document.querySelector('#logout').addEventListener('click',async()=>{try{await api('/logout',{method:'POST'});location.replace(base+'/login');}catch(ex){notify(ex.message);}});
document.querySelector('#projectCancel').addEventListener('click',()=>document.querySelector('#projectDialog').close());
document.querySelector('#projectClose').addEventListener('click',()=>document.querySelector('#projectDialog').close());
document.querySelector('#projectEnabled').addEventListener('click',()=>{const sw=document.querySelector('#projectEnabled');setProjectSwitch(sw.getAttribute('aria-checked')!=='true');});
document.querySelector('#projectFnAdd').addEventListener('click',addProjectFeature);
document.querySelector('#projectFnInput').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();addProjectFeature();}});
document.querySelector('#projectSave').addEventListener('click',async e=>{const data=collectProjectForm();if(!data.name){document.querySelector('#projectNameErr').hidden=false;document.querySelector('#projectName').focus();return;}const btn=e.currentTarget;btn.disabled=true;let saved=false;try{if(editingProjectId){await api('/projects/'+editingProjectId,{method:'PUT',body:JSON.stringify(data)});notify('项目已保存');}else{await api('/projects',{method:'POST',body:JSON.stringify(data)});notify('项目已创建');}saved=true;document.querySelector('#projectDialog').close();}catch(ex){notify(ex.message);}finally{btn.disabled=false;if(saved)load().catch(ex=>notify(ex.message));}});
// ---- 用户管理 ----
function setUserSwitch(on){const sw=document.querySelector('#userEnabled'),txt=document.querySelector('#userEnabledText');sw.classList.toggle('on',on);sw.setAttribute('aria-checked',String(on));txt.textContent=on?'启用':'停用';}
async function openUserForm(row){editingUserId=row?row.id:null;editingUserVersion=row?.row_version??null;let enabled=true,roleIds=[];if(row){try{const detail=await api('/users/'+row.id);row={...row,...detail};editingUserVersion=detail.row_version;roleIds=detail.role_ids;enabled=detail.is_enabled;}catch(ex){notify(ex.message);return;}}const dialog=document.querySelector('#userDialog');document.querySelector('#userFormTitle').textContent=row?'编辑用户':'新增用户';document.querySelector('#userName').value=row?row.display_name:'';document.querySelector('#userAccount').value=row?row.login_id:'';document.querySelector('#userNameErr').hidden=true;document.querySelector('#userAccountErr').hidden=true;selectedRoleIds=[...roleIds];setUserSwitch(enabled);roleDropdownOpen=false;document.querySelector('#userRoleSearch').value='';renderUserRoleDropdown();dialog.showModal();}
function renderUserRoleDropdown(){const trigger=document.querySelector('#userRoleTrigger');trigger.setAttribute('aria-expanded',String(roleDropdownOpen));document.querySelector('#userRoleTriggerText').textContent=selectedRoleIds.length?`已选择 ${selectedRoleIds.length} 个角色`:'请选择角色';document.querySelector('#userRoleDropdown').hidden=!roleDropdownOpen;const q=(document.querySelector('#userRoleSearch').value||'').trim().toLocaleLowerCase();const list=userRoleOptions.filter(r=>r.name.toLocaleLowerCase().includes(q));const box=document.querySelector('#userRoleOptions');box.replaceChildren();if(!list.length){box.append(el('div',userRoleOptions.length?'未找到匹配角色':'暂无角色，请先创建','user-role-empty'));}for(const r of list){const label=el('label',undefined,'user-role-option');const cb=el('input');cb.type='checkbox';cb.dataset.roleId=r.id;cb.checked=selectedRoleIds.includes(r.id);cb.addEventListener('change',()=>{if(cb.checked)selectedRoleIds=[...new Set([...selectedRoleIds,r.id])];else selectedRoleIds=selectedRoleIds.filter(x=>x!==r.id);renderUserRoleDropdown();});label.append(cb,el('span',r.name));if(!r.is_enabled)label.append(el('small','停用'));box.append(label);}const sel=document.querySelector('#userRoleSelected');sel.replaceChildren();if(!selectedRoleIds.length){sel.append(el('span','尚未选择角色','user-role-none'));return;}for(const id of selectedRoleIds){const r=userRoleOptions.find(x=>x.id===id);const tag=el('span',undefined,'user-role-tag');tag.append(document.createTextNode(r?r.name:id));const btn=el('button','×');btn.type='button';btn.title='移除角色';btn.addEventListener('click',()=>{selectedRoleIds=selectedRoleIds.filter(x=>x!==id);renderUserRoleDropdown();});tag.append(btn);sel.append(tag);}}
document.querySelector('#userRoleTrigger').addEventListener('click',()=>{roleDropdownOpen=!roleDropdownOpen;renderUserRoleDropdown();if(roleDropdownOpen)document.querySelector('#userRoleSearch').focus();});
document.querySelector('#userRoleSearch').addEventListener('input',()=>{if(roleDropdownOpen)renderUserRoleDropdown();});
document.querySelector('#userDialog').addEventListener('click',e=>{if(roleDropdownOpen&&!e.target.closest('#userRoleControl')){roleDropdownOpen=false;renderUserRoleDropdown();}});
document.querySelector('#userEnabled').addEventListener('click',()=>{const sw=document.querySelector('#userEnabled');setUserSwitch(sw.getAttribute('aria-checked')!=='true');});
document.querySelector('#userCancel').addEventListener('click',()=>document.querySelector('#userDialog').close());
document.querySelector('#userClose').addEventListener('click',()=>document.querySelector('#userDialog').close());
document.querySelector('#userSave').addEventListener('click',async e=>{const display_name=document.querySelector('#userName').value.trim();const login_id=document.querySelector('#userAccount').value.trim();let ok=true;if(!display_name){document.querySelector('#userNameErr').hidden=false;ok=false;}if(!login_id){document.querySelector('#userAccountErr').hidden=false;ok=false;}if(!ok)return;const is_enabled=document.querySelector('#userEnabled').getAttribute('aria-checked')==='true';const data={display_name,login_id,role_ids:selectedRoleIds,is_enabled,row_version:editingUserVersion};const btn=e.currentTarget;btn.disabled=true;let saved=false;try{if(editingUserId){await api('/users/'+editingUserId,{method:'PUT',body:JSON.stringify(data)});notify('用户已保存');}else{await api('/users',{method:'POST',body:JSON.stringify(data)});notify('用户已创建');}saved=true;document.querySelector('#userDialog').close();}catch(ex){notify(ex.message);}finally{btn.disabled=false;if(saved)load().catch(ex=>notify(ex.message));}});
// ---- 指标管理 ----
function metricCodePreview(catId){const cat=metricCategories.find(x=>x.id===Number(catId));return cat?cat.next_code:'';}
function setMetricUnit(unit){const sel=document.querySelector('#metricUnit');sel.querySelectorAll('[data-preserved-unit]').forEach(o=>o.remove());if(!Array.from(sel.options).some(o=>o.value===unit)){const o=el('option',unit||'待确认');o.value=unit;o.dataset.preservedUnit='1';sel.append(o);}sel.value=unit;}
function fillMetricDimSelect(catId){const sel=document.querySelector('#metricDim');sel.replaceChildren();for(const cat of metricCategories){const opt=el('option',cat.name);opt.value=cat.id;sel.append(opt);}if(catId)sel.value=String(catId);}
function fillMetricProjectSelect(projId){const sel=document.querySelector('#metricProject');sel.replaceChildren();const empty=el('option','请选择项目');empty.value='';sel.append(empty);for(const p of metricProjects.filter(p=>editingMetricId||p.can_create!==false)){const opt=el('option',p.name);opt.value=p.id;sel.append(opt);}if(projId)sel.value=String(projId);}
async function openMetricForm(row){editingMetricId=row?row.id:null;editingMetricVersion=row?.row_version??null;let catId=null,projId=null;if(row){try{const detail=await api('/metrics/'+row.id);editingMetricVersion=detail.row_version;catId=detail.category_id;projId=detail.project_id;document.querySelector('#metricName').value=detail.name;document.querySelector('#metricEnglish').value=detail.english_name;document.querySelector('#metricDef').value=detail.definition;document.querySelector('#metricBeidou').value=detail.beidou_metric_code;setMetricUnit(detail.unit||'');document.querySelector('#metricDecimalPlaces').value=String(detail.decimal_places??1);document.querySelector('#metricFormTitle').textContent='编辑指标';document.querySelector('#metricCode').value=detail.code;document.querySelector('#metricCodeHint').textContent='系统生成，保存后编码保持不变。';}catch(ex){notify(ex.message);return;}}else{document.querySelector('#metricFormTitle').textContent='新增指标';document.querySelector('#metricName').value='';document.querySelector('#metricEnglish').value='';document.querySelector('#metricDef').value='';document.querySelector('#metricBeidou').value='';document.querySelector('#metricUnit').value='人';document.querySelector('#metricDecimalPlaces').value='0';catId=metricCategories.length?metricCategories[0].id:null;projId=null;document.querySelector('#metricCodeHint').textContent='系统自动生成，保存时分配编码。';}fillMetricDimSelect(catId);fillMetricProjectSelect(projId);document.querySelector('#metricProject').disabled=!!row;document.querySelector('#metricProject').title=row?'指标所属项目创建后保持不变':'';document.querySelector('#metricCode').value=row?document.querySelector('#metricCode').value:metricCodePreview(catId);document.querySelector('#metricNameErr').hidden=true;document.querySelector('#metricNameErr').textContent='请填写指标名称';document.querySelector('#metricProjectErr').hidden=true;document.querySelector('#metricDialog').showModal();}
document.querySelector('#metricUnit').addEventListener('change',e=>{document.querySelector('#metricDecimalPlaces').value=String(({'人':0,'次':0,'%':1,'秒':2})[e.target.value]??1);});
document.querySelector('#metricDim').addEventListener('change',e=>{if(editingMetricId)return;document.querySelector('#metricCode').value=metricCodePreview(e.currentTarget.value);});
document.querySelector('#metricCancel').addEventListener('click',()=>document.querySelector('#metricDialog').close());
document.querySelector('#metricClose').addEventListener('click',()=>document.querySelector('#metricDialog').close());
document.querySelector('#metricSave').addEventListener('click',async e=>{const name=document.querySelector('#metricName').value.trim();const project_id=Number(document.querySelector('#metricProject').value);let ok=true;if(!name){const err=document.querySelector('#metricNameErr');err.textContent='请填写指标名称';err.hidden=false;ok=false;}if(!project_id){document.querySelector('#metricProjectErr').hidden=false;ok=false;}if(!ok)return;const data={name,row_version:editingMetricVersion,category_id:Number(document.querySelector('#metricDim').value),project_id,english_name:document.querySelector('#metricEnglish').value.trim(),unit:document.querySelector('#metricUnit').value,decimal_places:Number(document.querySelector('#metricDecimalPlaces').value),definition:document.querySelector('#metricDef').value.trim(),beidou_metric_code:document.querySelector('#metricBeidou').value.trim()};const btn=e.currentTarget;btn.disabled=true;let saved=false;try{if(editingMetricId){await api('/metrics/'+editingMetricId,{method:'PUT',body:JSON.stringify(data)});notify('指标已保存');}else{await api('/metrics',{method:'POST',body:JSON.stringify(data)});notify('指标已创建');}saved=true;document.querySelector('#metricDialog').close();}catch(ex){if(ex.message.includes('同名')){const err=document.querySelector('#metricNameErr');err.textContent=ex.message;err.hidden=false;}else{notify(ex.message);}}finally{btn.disabled=false;if(saved)load().catch(ex=>notify(ex.message));}});
// 所有模态弹窗：点击遮罩或按 ESC 关闭，避免弹窗关不掉
for(const id of ['confirmDialog','roleDialog','projectDialog','userDialog','metricDialog']){const dlg=document.querySelector('#'+id);if(!dlg)continue;dlg.addEventListener('click',e=>{if(e.target===dlg){dlg.close();}});dlg.addEventListener('cancel',e=>{e.preventDefault();dlg.close();});}

// ==================== 数据维护 ====================
let mtBoot=null,mtValues=new Map(),mtDraft=new Map(),mtStash=new Map();
let mtProject=null,mtDate='',mtStatus='idle',mtMsg='',mtSaving=false,mtCanEdit=false,mtDataReady=false,mtRequestVersion=0;
let mtVersions=new Map(),mtView='entry',mtImport={file:null,name:'',preview:null,result:null,busy:false,error:''},mtHistory=null,mtHistoryVersion=0,mtHistoryFilter={category:'',stat_date:'',source:'',metric:''};
const mtKey=(mid,fid)=>mid+'_'+(fid||0);
function mtToday(){return mtBoot?.today||new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Shanghai'});}
function mtShiftDate(d,days){const t=new Date(d+'T00:00:00');t.setDate(t.getDate()+days);return t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0');}
async function loadMaintain(){try{mtBoot=await api('/maintain/bootstrap');}catch(ex){mtBoot=null;mtDataReady=false;throw ex;}
 if(!mtProject||!mtBoot.projects.some(p=>p.id===mtProject))mtProject=mtBoot.projects[0]?.id??null;
 if(!mtDate)mtDate=mtToday();await mtLoadData();}
async function mtLoadData(){const request=++mtRequestVersion,project=mtProject,date=mtDate;mtDataReady=false;mtValues=new Map();mtVersions=new Map();mtStatus='loading';
 mtCanEdit=!!mtBoot?.projects.find(p=>p.id===project)?.can_edit;
 if(!project||!date){mtStatus='idle';return true;}
 try{const d=await api('/maintain/data?project_id='+project+'&stat_date='+date);if(request!==mtRequestVersion||project!==mtProject||date!==mtDate)return false;
  mtValues=new Map(d.items.map(r=>[mtKey(r.metric_id,r.feature_id),String(r.value)]));mtVersions=new Map(d.items.map(r=>[mtKey(r.metric_id,r.feature_id),r.row_version]));mtDataReady=true;mtStatus='idle';return true;
 }catch(ex){if(request!==mtRequestVersion)return false;mtStatus='error';mtMsg='读取失败：'+ex.message;mtDataReady=false;return true;}}
function mtSwitchProject(id){if(mtSaving||!mtBoot||id===mtProject)return;mtStash.set(mtProject+'|'+mtDate,new Map(mtDraft));mtProject=id;mtHistory=null;mtDraft=new Map(mtStash.get(mtProject+'|'+mtDate)||[]);mtValues=new Map();mtDataReady=false;mtStatus='loading';render();mtLoadData().then(current=>{if(current)render();});}
function mtSwitchDate(d){if(mtSaving||d===mtDate||d>mtToday())return;mtStash.set(mtProject+'|'+mtDate,new Map(mtDraft));mtDate=d;mtDraft=new Map(mtStash.get(mtProject+'|'+mtDate)||[]);mtValues=new Map();mtDataReady=false;mtStatus='loading';render();mtLoadData().then(current=>{if(current)render();});}
function mtIsDirty(){for(const [k,v] of mtDraft){const a=mtValues.has(k)?mtValues.get(k):'';if((v||'')!==a)return true;}return false;}
function mtMetricsOf(catId){return mtBoot?mtBoot.metrics.filter(m=>m.project_id===mtProject&&m.category_id===catId):[];}
function mtFeaturesOf(){return mtBoot?mtBoot.features.filter(f=>f.project_id===mtProject):[];}
function updateSavebar(msg){const bar=document.querySelector('#savebar');if(!bar||bar.hidden)return;
 const state=document.querySelector('#saveState');const btn=document.querySelector('#saveMaintainBtn');
 if(!state||!btn)return;
 btn.disabled=mtSaving||!mtCanEdit||!mtDataReady;
 btn.textContent=mtCanEdit?'保存数据':'无编辑权限';
 let text=msg;
 if(!text){if(mtStatus==='loading')text='正在加载数据…';else if(mtSaving)text='正在保存…';else if(mtStatus==='error')text=mtMsg;else if(mtIsDirty())text='有未保存的更改';else if(mtStatus==='saved')text=mtMsg||'所有更改已保存';else text='暂无更改';}
 state.textContent=text;state.className=mtStatus==='error'?'save-state error':(mtIsDirty()?'save-state dirty':'save-state');}
function mtFieldBlock(m,fid,compact){const k=mtKey(m.id,fid);
 const wrap=el('div',undefined,'maint-field');wrap.id='wrap-'+k;
 const box=el('div',undefined,'maint-input');
 const inp=document.createElement('input');inp.id='mt-'+k;
 inp.inputmode=(m.unit==='人'||m.unit==='次')?'numeric':'decimal';
 inp.autocomplete='off';inp.placeholder=(m.unit==='人'||m.unit==='次')?'请输入人数或次数':'请输入数值';
 inp.disabled=!mtDataReady||!mtCanEdit||mtSaving||(mtBoot.categories.find(c=>c.id===m.category_id)?.code==='retention'&&mtDate>=mtToday());inp.value=mtDraft.has(k)?(mtDraft.get(k)||''):(mtValues.get(k)||'');
 if(compact)inp.setAttribute('aria-label',m.name);
 box.append(inp);
 box.append(el('span',m.unit||'单位待确认','maint-unit'));
 const err=el('div','','maint-error');err.id='err-'+k;
 inp.addEventListener('input',()=>{mtDraft.set(k,inp.value.trim());err.textContent='';wrap.classList.remove('invalid');mtStatus='dirty';updateSavebar();});
 wrap.append(box,err);
 if(compact)return wrap;
 const lab=el('label',undefined,'maint-label');lab.htmlFor='mt-'+k;
 lab.append(el('span',m.name,'maint-name'));
 if(m.definition){const tip=el('span','?','maint-help');tip.title=m.definition;lab.append(tip);}
 wrap.prepend(lab);return wrap;}
function mtValidateAll(items,errs){
 for(const [k,v] of mtDraft){const parts=k.split('_');const mid=Number(parts[0]);const fid=parts[1]==='0'?null:Number(parts[1]);
  const m=mtBoot.metrics.find(x=>x.id===mid);if(!m||m.project_id!==mtProject)continue;
  const saved=mtValues.has(k)?mtValues.get(k):'';const dv=(v||'').trim();
  if(dv===(saved||''))continue;
  if(!dv){items.push({metric_id:mid,feature_id:fid,value:null,expected_version:mtVersions.get(k)||0});continue;}
  const isInt=(m.unit==='人'||m.unit==='次');
  const dp=(m.decimal_places!=null&&m.decimal_places>=0&&m.decimal_places<=6)?m.decimal_places:6;
  let errmsg='';
  if(isInt&&!/^\d+$/.test(dv))errmsg='请输入非负整数';
  else if(!isInt&&!(dp===0?/^\d+$/:new RegExp('^\\d+(\\.\\d{1,'+dp+'})?$')).test(dv))errmsg='请输入非负数，最多 '+dp+' 位小数';
  else if(m.unit==='%'&&Number(dv)>100)errmsg='比例应在 0～100 之间';
  if(errmsg)errs.set(k,errmsg);else items.push({metric_id:mid,feature_id:fid,value:dv,expected_version:mtVersions.get(k)||0});}}
async function saveMaintain(){if(mtSaving||!mtCanEdit||!mtDataReady)return;
 const items=[],errs=new Map();mtValidateAll(items,errs);
 for(const [k,msg] of errs){const err=document.querySelector('#err-'+CSS.escape(k)),wrap=document.querySelector('#wrap-'+CSS.escape(k));if(err)err.textContent=msg;if(wrap)wrap.classList.add('invalid');}
 if(errs.size){notify('请先修正录入错误','center');return;}
 if(!items.length){notify('暂无需要保存的更改','center');return;}
 const project=mtProject,date=mtDate;mtSaving=true;mtStatus='saving';render();
 try{const result=await api('/maintain/data',{method:'POST',body:JSON.stringify({project_id:project,stat_date:date,items})});
  if(project===mtProject&&date===mtDate){for(const item of items){const key=mtKey(item.metric_id,item.feature_id);if(item.value===null)mtValues.delete(key);else mtValues.set(key,item.value);mtDraft.delete(key);}
   for(const v of result.versions||[])mtVersions.set(mtKey(v.metric_id,v.feature_id),v.row_version);
   mtStash.set(project+'|'+date,new Map(mtDraft));mtStatus='saved';mtMsg='已保存 '+result.saved+' 项更改';notify('数据保存成功','center');}
 }catch(ex){if(project===mtProject&&date===mtDate){mtStatus='error';mtMsg=ex.message;if(ex.message.includes('更新'))mtDataReady=false;}notify(ex.message,'center');}
 finally{mtSaving=false;render();}}
function mtSection(cat){const metrics=mtMetricsOf(cat.id);
 const section=el('section',undefined,'card maint-section');section.dataset.cat=cat.code;
 const head=el('div',undefined,'maint-head');head.append(el('h2',cat.name));
 const hints={coverage:'截至所选统计日的累计数据',activity:'按所选自然日录入',depth:'有效会话数口径待确认时仍可录入',retention:'基准日 '+mtShiftDate(mtDate,-7).replaceAll('-','.')+' → 第 7 天观察日 '+mtDate.replaceAll('-','.'),performance:'同一批成功请求，均从发送指令开始计时',feature:'按项目功能逐行录入当日及累计使用数据',funnel:'维护当前项目已启用的漏斗指标'};
 if(hints[cat.code])head.append(el('span',hints[cat.code],'maint-hint'));
 section.append(head);
 if(cat.code==='retention'&&mtDate>=mtToday()){const warn=el('p','统计日期为观察日；7 日留存仅可录入今天之前已结束的观察日。','maint-warn');section.append(warn);}
 if(cat.code==='feature'){const features=mtFeaturesOf();
  if(!features.length){section.append(el('p','该项目尚未配置功能清单，请先到「项目管理」中维护。','maint-empty'));return section;}
  if(!metrics.length){section.append(el('p','当前项目暂无已启用的功能使用指标，请先到「指标管理」中维护。','maint-empty'));return section;}
  const wrap=el('div',undefined,'table-wrap');const table=el('table',undefined,'maint-feature-table');
  const thead=el('thead'),trh=el('tr');trh.append(el('th','功能'));
  trh.append(...metrics.map(m=>{const th=el('th');const line=el('span',undefined,'maint-th-line');line.append(el('span',m.name+(m.unit?'（'+m.unit+'）':'')));if(m.definition){const tip=el('span','?','maint-help');tip.title=m.definition;line.append(tip);}th.append(line);return th;}));
  thead.append(trh);table.append(thead);
  const tbody=el('tbody');
  for(const f of features){const tr=el('tr');tr.append(el('td',f.name,'maint-feature-name'));
   for(const m of metrics){const td=el('td');td.append(mtFieldBlock(m,f.id,true));tr.append(td);}
   tbody.append(tr);}
  table.append(tbody);wrap.append(table);section.append(wrap);
  section.append(el('p','日使用人数占比以当日活跃用户数为分母，累计使用人数占比以项目累计使用用户数为分母；各功能分别去重，占比之和可能超过 100%。','maint-foot'));
  return section;}
 if(!metrics.length){if(cat.code==='funnel')section.append(el('p','当前项目暂无已启用的漏斗指标，请先到「指标管理」中新增并关联适用项目。','maint-empty'));return section;}
 const grid=el('div',undefined,'maint-grid');
 for(const m of metrics)grid.append(mtFieldBlock(m,0));
 section.append(grid);return section;}
function renderMaintain(){content.replaceChildren();
 if(!mtBoot){content.replaceChildren(el('p','数据维护 / 指标录入','breadcrumb'),el('p','配置加载失败，请刷新重试。','form-error'));return;}
 if(mtView==='history'){renderMaintainHistoryPage();return;}
 content.append(el('p','数据维护','breadcrumb'));
 const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');
 titleRow.append(el('h1','指标数据维护'),el('p','按项目、统计日期维护已启用指标的数值数据。','subtitle'));
 heading.append(titleRow);content.append(heading);
 const ctx=el('div',undefined,'mt-context');const ctxLeft=el('div',undefined,'mt-context-left');
 const tabs=el('div',undefined,'mt-tabs');tabs.setAttribute('role','group');tabs.setAttribute('aria-label','切换项目');
 for(const p of mtBoot.projects){const b=el('button',p.name,'mt-tab'+(p.id===mtProject?' active':''));b.type='button';b.disabled=mtSaving;b.setAttribute('aria-pressed',String(p.id===mtProject));b.addEventListener('click',()=>mtSwitchProject(p.id));tabs.append(b);}
 ctxLeft.append(tabs);
 const dateRow=el('div',undefined,'mt-date-row');
 const dateLabel=el('label','统计日期','mt-date-label');
 const stepper=el('div',undefined,'mt-stepper');
 const prevBtn=el('button');prevBtn.type='button';prevBtn.disabled=mtSaving;prevBtn.setAttribute('aria-label','前一天');prevBtn.innerHTML=ic('<path d="m15 18-6-6 6-6"/>');
 prevBtn.addEventListener('click',()=>mtSwitchDate(mtShiftDate(mtDate,-1)));
 const dateInput=document.createElement('input');dateInput.type='date';dateInput.disabled=mtSaving;dateInput.id='mtDateInput';dateInput.value=mtDate;dateInput.max=mtToday();
 dateInput.addEventListener('change',()=>{if(dateInput.value)mtSwitchDate(dateInput.value);});
 const nextBtn=el('button');nextBtn.type='button';nextBtn.setAttribute('aria-label','后一天');nextBtn.innerHTML=ic('<path d="m9 18 6-6-6-6"/>');
 nextBtn.disabled=mtSaving||mtDate>=mtToday();
 nextBtn.addEventListener('click',()=>mtSwitchDate(mtShiftDate(mtDate,1)));
 stepper.append(prevBtn,dateInput,nextBtn);
 dateLabel.htmlFor='mtDateInput';
 dateRow.append(dateLabel,stepper);
 if(mtIsDirty())dateRow.append(el('span','当前项目与日期下有未保存的更改，切换后将保留草稿。','mt-dirty-note'));
 ctxLeft.append(dateRow);ctx.append(ctxLeft);const headActions=el('div',undefined,'page-heading-actions');
 headActions.append(buildImportDropdown(),buildHistoryButton());ctx.append(headActions);content.append(ctx);if(mtStatus==='error'){const error=el('div',undefined,'error-banner');error.append(el('p',mtMsg));const retry=el('button','重新加载数据','secondary');retry.onclick=async()=>{if(mtIsDirty()&&!confirm('重新加载会放弃当前未保存的修改，是否继续？'))return;mtDraft.clear();mtStash.delete(mtProject+'|'+mtDate);await mtLoadData();render();};error.append(retry);content.append(error);} if(!mtBoot.projects.length)content.append(el('p','暂无有权访问的启用项目','maint-empty'));
 const grid=el('div',undefined,'maint-sections');
 for(const cat of mtBoot.categories)grid.append(mtSection(cat));
 content.append(grid);
 updateSavebar();}
document.querySelector('#saveMaintainBtn').addEventListener('click',saveMaintain);
document.addEventListener('click',e=>{const dd=document.querySelector('.mt-dd.open');if(dd&&!dd.contains(e.target))dd.classList.remove('open');});
document.querySelector('#mtImportClose').addEventListener('click',()=>document.querySelector('#maintImportDialog').close());
document.querySelector('#mtImportPick').addEventListener('click',()=>document.querySelector('#mtImportFile').click());
document.querySelector('#mtImportFile').addEventListener('change',async e=>{const selected=e.target.files[0];if(!selected)return;
 if(selected.size>2*1024*1024){notify('文件不能超过 2 MB');e.target.value='';return;}
 if(!/\.xlsx$/i.test(selected.name)){notify('请选择 .xlsx 文件');e.target.value='';return;}
 mtImport.busy=true;mtImport.error='';mtImport.preview=null;mtImport.result=null;mtImportDialogRefresh();
 try{const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('无法读取文件'));reader.readAsDataURL(selected);});
  mtImport.file=data;mtImport.name=selected.name;}
 catch(ex){mtImport.file=null;mtImport.error='无法读取 Excel 文件，请重试';}
 mtImport.busy=false;mtImportDialogRefresh();});
document.querySelector('#mtImportValidate').addEventListener('click',validateMaintainImport);
document.querySelector('#mtImportCommit').addEventListener('click',commitMaintainImport);
document.querySelector('#mtImportReport').addEventListener('click',downloadMaintainImportReport);

// ==================== 漏斗管理 ====================
let funnels=[],funnelOptions=[],funnelProjects=[],funnelsCanCreate=false,funnelsCanEdit=false;
let funnelEdit=null,funnelDragIndex=null;
function funnelOptionsFor(project){return funnelOptions.filter(o=>String(o.project_id)===project&&o.category_code==='funnel');}
function renderFunnels(){content.replaceChildren();
 content.append(el('p','设置管理 / 漏斗管理','breadcrumb'));
 const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');
 titleRow.append(el('h1','漏斗管理'),el('p','配置各项目的功能漏斗名称与步骤，首页按此展示漏斗转化。','subtitle'));
 heading.append(titleRow);
 const addBtn=el('button',undefined,'primary');addBtn.innerHTML=ICONS.plus+'新增漏斗';addBtn.disabled=!funnelsCanCreate;
 addBtn.addEventListener('click',()=>openFunnelEditor(null));heading.append(addBtn);
 content.append(heading);
 const card=el('section',undefined,'card');
 const wrap=el('div',undefined,'table-wrap'),table=el('table');table.setAttribute('aria-label','漏斗管理');
 const head=el('thead'),trh=el('tr');
 [['漏斗名称',null],['适用项目',220],['步骤数',110],['状态',110],['操作',110]].forEach(([t,w])=>{const th=el('th',t);if(w)th.style.width=w+'px';trh.append(th);});
 head.append(trh);table.append(head);
 const body=el('tbody');
 if(!funnels.length){const empty=el('tr');const td=el('td','暂无漏斗，点击右上角「新增漏斗」创建。');td.colSpan=5;td.style.textAlign='center';td.style.color='#7c8ba1';td.style.padding='40px';empty.append(td);body.append(empty);}
 for(const row of pagedList('funnels',funnels)){const r=el('tr');
  const nameTd=el('td');nameTd.append(el('strong',row.name));r.append(nameTd);
  r.append(el('td',row.project_name||'—'));
  r.append(el('td',String(row.steps.length)));
  const status=el('td');status.append(el('span',row.is_enabled?'启用':'停用','status '+(row.is_enabled?'enabled':'disabled')));r.append(status);
  const action=el('td'),actBox=el('div',undefined,'order-btns');
  const editBtn=el('button',undefined,'icon-btn');editBtn.innerHTML=ICONS.edit;editBtn.title='编辑';editBtn.setAttribute('aria-label','编辑漏斗'+row.name);editBtn.disabled=!funnelsCanEdit||row.can_edit===false;
  editBtn.addEventListener('click',()=>openFunnelEditor(row));
  const toggleBtn=el('button',undefined,'icon-btn'+(row.is_enabled?'':' play-green'));toggleBtn.innerHTML=row.is_enabled?ICONS.pause:ICONS.play;
  toggleBtn.title=row.is_enabled?'停用':'启用';toggleBtn.setAttribute('aria-label',(row.is_enabled?'停用':'启用')+'漏斗'+row.name);
  toggleBtn.disabled=row.is_enabled?row.can_disable===false:row.can_enable===false;toggleBtn.addEventListener('click',()=>confirmFunnelChange(row));
  actBox.append(editBtn,toggleBtn);action.append(actBox);r.append(action);
  body.append(r);}
 table.append(body);wrap.append(table);card.append(wrap);content.append(card);
 content.append(buildPager('funnels','漏斗'));}
function confirmFunnelChange(row){pending=row;const action=row.is_enabled?'停用':'启用';
 document.querySelector('#confirmTitle').textContent=action+'漏斗';
 document.querySelector('#confirmText').textContent='确认'+action+'“'+row.name+'”？'+(row.is_enabled?'停用后首页将不再展示该漏斗。':'该漏斗将恢复在首页展示。');
 document.querySelector('#confirmChange').textContent='确认'+action;
 document.querySelector('#confirmDialog').showModal();}
function openFunnelEditor(row){funnelEdit=row?{id:row.id,row_version:row.row_version,name:row.name,project:String(row.project_id),
  steps:row.steps.map(s=>({name:s.step_name,binding:String(s.binding_id)})),errors:{},saving:false}
  :{id:null,name:'',project:'',steps:[],errors:{},saving:false};
 content.replaceChildren();renderFunnelEditor();}
function closeFunnelEditor(){funnelEdit=null;render();}
function changeFunnelProject(project){const d=funnelEdit;if(!d||project===d.project)return;
 d.project=project;d.steps.forEach(s=>s.binding='');d.errors={};content.replaceChildren();renderFunnelEditor();}
function addFunnelStep(){const d=funnelEdit;if(!d||!d.project)return;d.steps.push({name:'',binding:''});
 content.replaceChildren();renderFunnelEditor();
 const inp=document.querySelector('#funnel-step-name-'+(d.steps.length-1));if(inp)inp.focus();}
function removeFunnelStep(i){const d=funnelEdit;if(!d)return;d.steps.splice(i,1);d.errors={};content.replaceChildren();renderFunnelEditor();}
function moveFunnelStep(from,to){const d=funnelEdit;if(!d||!d.project)return;
 if(!Number.isInteger(from)||!Number.isInteger(to)||from<0||to<0||from>=d.steps.length||to>=d.steps.length||from===to)return;
 const [step]=d.steps.splice(from,1);d.steps.splice(to,0,step);d.errors={};funnelDragIndex=null;
 content.replaceChildren();renderFunnelEditor();
 const handle=document.querySelector('#funnel-step-drag-'+to);if(handle)handle.focus();}
function funnelStepDragHandlers(){
 document.querySelectorAll('[data-step-drag]').forEach(handle=>{
  handle.addEventListener('dragstart',e=>{const d=funnelEdit;if(!d.project){e.preventDefault();return;}
   funnelDragIndex=Number(handle.dataset.stepDrag);e.dataTransfer.effectAllowed='move';
   e.dataTransfer.setData('text/plain',String(funnelDragIndex));handle.closest('tr').classList.add('drag-source');});
  handle.addEventListener('dragend',()=>{funnelDragIndex=null;
   document.querySelectorAll('[data-funnel-step-row]').forEach(r=>r.classList.remove('drag-source','drop-before','drop-after'));});
  handle.addEventListener('keydown',e=>{if(e.key!=='ArrowUp'&&e.key!=='ArrowDown')return;e.preventDefault();
   const i=Number(handle.dataset.stepDrag);moveFunnelStep(i,i+(e.key==='ArrowUp'?-1:1));});});
 document.querySelectorAll('[data-funnel-step-row]').forEach(row=>{
  const after=e=>e.clientY>row.getBoundingClientRect().top+row.getBoundingClientRect().height/2;
  row.addEventListener('dragover',e=>{if(funnelDragIndex===null)return;e.preventDefault();e.dataTransfer.dropEffect='move';
   document.querySelectorAll('[data-funnel-step-row]').forEach(r=>r.classList.remove('drop-before','drop-after'));
   row.classList.add(after(e)?'drop-after':'drop-before');});
  row.addEventListener('dragleave',e=>{if(!row.contains(e.relatedTarget))row.classList.remove('drop-before','drop-after');});
  row.addEventListener('drop',e=>{if(funnelDragIndex===null)return;e.preventDefault();
   const from=funnelDragIndex,index=Number(row.dataset.funnelStepRow);
   const insertion=index+(after(e)?1:0),to=insertion-(from<insertion?1:0);
   funnelDragIndex=null;moveFunnelStep(from,to);});});}
function renderFunnelEditor(){const d=funnelEdit;if(!d){renderFunnels();return;}
 const title=d.id?'编辑漏斗':'新增漏斗';
 content.replaceChildren();
 content.append(el('p','设置管理 / 漏斗管理 / '+title,'breadcrumb'));
 const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');
 titleRow.append(el('h1',title),el('p','配置漏斗名称、适用项目和步骤指标。','subtitle'));
 const backBtn=el('button',undefined,'secondary');backBtn.textContent='返回列表';
 backBtn.addEventListener('click',closeFunnelEditor);
 heading.append(titleRow,backBtn);content.append(heading);
 const opts=d.project?funnelOptionsFor(d.project):[];
 // 基本信息
 const card1=el('section',undefined,'card funnel-panel');
 const grid=el('div',undefined,'funnel-grid2');
 const nameField=el('div',undefined,'funnel-field'+(d.errors.name?' invalid':''));
 const nameLabel=el('label',undefined,'funnel-field-label');nameLabel.htmlFor='funnelName';
 nameLabel.append(el('span','*','req'),el('span','漏斗名称'));nameField.append(nameLabel);
 const nameInput=document.createElement('input');nameInput.id='funnelName';nameInput.type='text';
 nameInput.value=d.name;nameInput.placeholder='请输入漏斗名称';nameInput.maxLength=100;
 nameInput.addEventListener('input',()=>{d.name=nameInput.value;});
 nameField.append(nameInput);
 if(d.errors.name)nameField.append(el('div',d.errors.name,'funnel-field-error'));
 grid.append(nameField);
 const projField=el('div',undefined,'funnel-field'+(d.errors.project?' invalid':''));
 const projLabel=el('label',undefined,'funnel-field-label');projLabel.htmlFor='funnelProject';
 projLabel.append(el('span','*','req'),el('span','适用项目'));projField.append(projLabel);
 const projSel=document.createElement('select');projSel.id='funnelProject';
 const defOpt=document.createElement('option');defOpt.value='';defOpt.textContent='请选择适用项目';projSel.append(defOpt);
 for(const p of funnelProjects){const o=document.createElement('option');o.value=String(p.id);
  o.textContent=p.name+(p.is_enabled?'':'（已停用）');if(String(p.id)===d.project)o.selected=true;projSel.append(o);}
 projSel.addEventListener('change',()=>changeFunnelProject(projSel.value));
 projField.append(projSel);
 if(d.errors.project)projField.append(el('div',d.errors.project,'funnel-field-error'));
 grid.append(projField);card1.append(grid);content.append(card1);
 // 漏斗步骤
 const card2=el('section',undefined,'card funnel-panel');
 const toolbar=el('div',undefined,'funnel-editor-toolbar');
 toolbar.append(el('h2','漏斗步骤'));
 const addStepBtn=el('button',undefined,'secondary');addStepBtn.innerHTML=ICONS.plus+'添加步骤';
 addStepBtn.disabled=!d.project;addStepBtn.addEventListener('click',addFunnelStep);
 toolbar.append(addStepBtn);card2.append(toolbar);
 const hint=d.project
   ?(opts.length?'拖动步骤左侧手柄调整顺序，也可使用上下方向键；每步仅可选择当前项目已启用的「漏斗指标」。':'该项目暂无可选的漏斗指标，请先在指标管理中维护类型为「漏斗指标」的适用指标。')
   :'请先选择适用项目，再添加或编辑漏斗步骤。';
 card2.append(el('p',hint,'funnel-editor-hint'));
 if(d.errors.stages)card2.append(el('div',d.errors.stages,'funnel-field-error'));
 if(!d.steps.length){card2.append(el('p','暂无步骤，点击「添加步骤」开始配置。','funnel-steps-empty'));}
 else{const wrap=el('div',undefined,'table-wrap');const table=el('table',undefined,'funnel-step-table');
  const thead=el('thead'),trh=el('tr');
  [['步骤',100],['步骤名称',null],['选择指标',null],['操作',70]].forEach(([t,w])=>{const th=el('th',t);if(w)th.style.width=w+'px';trh.append(th);});
  thead.append(trh);table.append(thead);
  const tbody=el('tbody');
  d.steps.forEach((step,i)=>{const tr=el('tr');tr.dataset.funnelStepRow=String(i);
   const orderTd=el('td');const orderBox=el('div',undefined,'funnel-step-order');
   const handle=el('button',undefined,'funnel-drag-handle');handle.type='button';handle.id='funnel-step-drag-'+i;
   handle.dataset.stepDrag=String(i);handle.draggable=!!d.project;handle.title='拖动排序，也可使用上下方向键';
   handle.setAttribute('aria-label','调整步骤 '+(i+1)+' 顺序');
   handle.innerHTML='<svg viewBox="0 0 16 20" width="14" height="18" fill="currentColor" aria-hidden="true"><circle cx="5" cy="5" r="1.5"/><circle cx="11" cy="5" r="1.5"/><circle cx="5" cy="10" r="1.5"/><circle cx="11" cy="10" r="1.5"/><circle cx="5" cy="15" r="1.5"/><circle cx="11" cy="15" r="1.5"/></svg>';
   orderBox.append(handle,el('span',String(i+1),'step-number'));orderTd.append(orderBox);tr.append(orderTd);
   const nameTd=el('td',undefined,'funnel-step-name-cell');
   const nameInp=document.createElement('input');nameInp.id='funnel-step-name-'+i;nameInp.type='text';
   nameInp.value=step.name;nameInp.placeholder='请输入步骤名称';nameInp.maxLength=100;
   nameInp.addEventListener('input',()=>{d.steps[i].name=nameInp.value;});
   nameTd.append(nameInp);
   if(d.errors['name'+i])nameTd.append(el('div',d.errors['name'+i],'funnel-field-error'));
   tr.append(nameTd);
   const metricTd=el('td',undefined,'funnel-step-metric-cell');
   const mSel=document.createElement('select');mSel.id='funnel-step-metric-'+i;
   const mDef=document.createElement('option');mDef.value='';
   mDef.textContent=step.binding&&!opts.some(o=>String(o.binding_id)===step.binding)?'原指标已停用、类型不符或不适用，请重新选择':'请选择指标';
   mSel.append(mDef);
   for(const o of opts){const op=document.createElement('option');op.value=String(o.binding_id);
    op.textContent=o.metric_name+(o.unit?'（'+o.unit+'）':'')+' · '+o.metric_code+(o.feature_name?' · '+o.feature_name:'');
    if(step.binding===String(o.binding_id))op.selected=true;mSel.append(op);}
   mSel.addEventListener('change',()=>{d.steps[i].binding=mSel.value;});
   metricTd.append(mSel);
   if(d.errors['metric'+i])metricTd.append(el('div',d.errors['metric'+i],'funnel-field-error'));
   tr.append(metricTd);
   const opTd=el('td');const delBtn=el('button',undefined,'icon-btn');delBtn.innerHTML=ICONS.trash;
   delBtn.title='删除步骤';delBtn.setAttribute('aria-label','删除步骤 '+(i+1));
   delBtn.addEventListener('click',()=>removeFunnelStep(i));opTd.append(delBtn);tr.append(opTd);
   tbody.append(tr);});
  table.append(tbody);wrap.append(table);card2.append(wrap);}
 content.append(card2);
 // 操作区
 const actions=el('div',undefined,'funnel-editor-actions');
 const cancelBtn=el('button',undefined,'secondary');cancelBtn.textContent='取消';
 cancelBtn.addEventListener('click',closeFunnelEditor);
 const saveBtn=el('button',undefined,'primary');saveBtn.textContent='保存漏斗';saveBtn.id='saveFunnelBtn';
 saveBtn.addEventListener('click',saveFunnel);
 actions.append(cancelBtn,saveBtn);content.append(actions);
 funnelStepDragHandlers();}
function validateFunnelClient(d){const errors={};
 if(!d.name.trim())errors.name='请填写漏斗名称';
 if(!d.project)errors.project='请选择适用项目';
 if(!d.steps.length)errors.stages='请至少添加一个漏斗步骤';
 const allowed=new Set(funnelOptionsFor(d.project).map(o=>String(o.binding_id)));
 d.steps.forEach((s,i)=>{if(!s.name.trim())errors['name'+i]='请填写步骤名称';
  if(!allowed.has(s.binding))errors['metric'+i]='请选择适用项目内已启用的「漏斗指标」';});
 return errors;}
async function saveFunnel(){const d=funnelEdit;if(!d||d.saving)return;
 d.errors=validateFunnelClient(d);
 if(Object.keys(d.errors).length){content.replaceChildren();renderFunnelEditor();return;}
 const btn=document.querySelector('#saveFunnelBtn');d.saving=true;if(btn)btn.disabled=true;
 const payload={row_version:d.row_version??null,project_id:Number(d.project),name:d.name.trim(),
  steps:d.steps.map(s=>({step_name:s.name.trim(),binding_id:Number(s.binding)}))};
 let saved=false;
 try{if(d.id)await api('/funnels/'+d.id,{method:'PUT',body:JSON.stringify(payload)});
  else await api('/funnels',{method:'POST',body:JSON.stringify(payload)});
  saved=true;}
 catch(ex){d.errors={stages:ex.message};}
 d.saving=false;if(btn)btn.disabled=false;
 if(saved){notify('漏斗已保存');funnelEdit=null;render();load().catch(()=>{});}
 else{content.replaceChildren();renderFunnelEditor();}}

for(const form of document.querySelectorAll("dialog form")){form.addEventListener("submit",e=>e.preventDefault());}

async function downloadImportFile(path,name){
 const response=await fetch(base+'/api'+path,{headers:{'X-CSRF-Token':user.csrf_token}});
 if(response.status===401){location.replace(base+'/login');throw Error('请重新登录');}
 if(!response.ok){let error;try{error=await response.json();}catch{}throw Error(error?.detail||'文件下载失败');}
 const blob=await response.blob(),url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function downloadMaintainTemplate(){try{await downloadImportFile('/maintain/import/template?stat_date='+encodeURIComponent(mtDate),'指标批量导入模板.xlsx');}catch(e){notify(e.message);}}
async function downloadMaintainImportReport(){const data=mtImport.result||mtImport.preview;if(!data)return;try{await downloadImportFile('/maintain/import/excel/'+data.batch_id+'/report',mtImport.name.replace(/\.xlsx$/i,'')+'_导入结果.xlsx');}catch(e){notify(e.message);}}
async function validateMaintainImport(){if(!mtImport.file||mtImport.busy)return;mtImport.busy=true;mtImport.error='';mtImport.preview=null;mtImport.result=null;mtImportDialogRefresh();
 try{const data=await api('/maintain/import/excel/preview',{method:'POST',body:JSON.stringify({file_name:mtImport.name,file_base64:mtImport.file})});mtImport.preview=data;mtImport.result=null;}
 catch(e){mtImport.error=e.message;mtImport.preview=null;}
 mtImport.busy=false;mtImportDialogRefresh();}
async function commitMaintainImport(){const state=mtImport;if(state.busy||!state.preview?.counts.valid)return;state.busy=true;mtSaving=true;mtImportDialogRefresh();
 try{const result=await api('/maintain/import/excel/'+state.preview.batch_id+'/commit',{method:'POST',body:'{}'});state.result=result;state.preview=null;mtHistory=null;}
 catch(e){state.error=e.message;}
 state.busy=false;mtSaving=false;mtImportDialogRefresh();
 if(state.result){await mtLoadData();render();
  if(state.result.phase==='completed'){const dlg=document.querySelector('#maintImportDialog');if(dlg&&dlg.open)dlg.close();notify('导入完成，共写入 '+state.result.counts.inserted+' 条新增、'+state.result.counts.updated+' 条更新');}}}
function buildImportDropdown(){const wrap=el('div',undefined,'mt-dd');
 const btn=el('button',undefined,'secondary');btn.type='button';btn.innerHTML=ICONS.down+'批量导入';btn.setAttribute('aria-haspopup','true');
 btn.addEventListener('click',e=>{e.stopPropagation();wrap.classList.toggle('open');});
 const menu=el('div',undefined,'mt-dd-menu');
 const tpl=el('button','下载模板','mt-dd-item');tpl.type='button';tpl.disabled=mtImport.busy;
 tpl.addEventListener('click',()=>{wrap.classList.remove('open');downloadMaintainTemplate();});
 const imp=el('button','数据导入','mt-dd-item');imp.type='button';imp.disabled=mtImport.busy||!mtBoot.projects.some(p=>p.can_import);
 imp.addEventListener('click',()=>{wrap.classList.remove('open');openMaintainImportDialog();});
 menu.append(tpl,imp);wrap.append(btn,menu);return wrap;}
function buildHistoryButton(){const b=el('button','修改记录','secondary');b.type='button';b.disabled=mtSaving;
 b.addEventListener('click',()=>{mtView='history';listPages.history.page=1;render();fetchMaintainHistory();});return b;}
function renderMaintainHistoryPage(){content.replaceChildren();
 content.append(el('p','数据维护 / 修改记录','breadcrumb'));
 const heading=el('div',undefined,'page-heading');const titleRow=el('div',undefined,'title-row');
 titleRow.append(el('h1','修改记录'),el('p','查看指标数据的保存与导入变更历史。','subtitle'));
 const back=el('button','返回数据维护','secondary');back.addEventListener('click',()=>{mtView='entry';render();});
 heading.append(titleRow,back);content.append(heading);
 document.querySelector('#savebar').hidden=true;
 renderMaintainAux(content);}
function openMaintainImportDialog(){mtImport.file=null;mtImport.name='';mtImport.preview=null;mtImport.result=null;mtImport.error='';mtImport.busy=false;
 document.querySelector('#maintImportDialog').showModal();mtImportDialogRefresh();}
function mtImportDialogRefresh(){const dlg=document.querySelector('#maintImportDialog');if(!dlg||!dlg.open)return;
 document.querySelector('#mtImportFileName').textContent=mtImport.name||'未选择文件';
 const validate=document.querySelector('#mtImportValidate');
 validate.disabled=!mtImport.file||mtImport.busy;validate.textContent=mtImport.busy?'校验中…':'数据校验';
 const data=mtImport.result||mtImport.preview;
 document.querySelector('#mtImportActions').hidden=!data;
 const commit=document.querySelector('#mtImportCommit');
 commit.hidden=!mtImport.preview||!!mtImport.result;
 commit.disabled=mtImport.busy||!mtImport.preview?.counts.valid;
 const status=document.querySelector('#mtImportStatus');status.replaceChildren();
 if(mtImport.error)status.append(el('p',mtImport.error,'form-error'));
 if(mtImport.preview){const c=mtImport.preview.counts;
  status.append(el('p','导入数据 '+c.total+' 条，有效数据 '+c.valid+' 条，无效数据 '+c.invalid+' 条。其中新增数据 '+c.insert+' 条，更新数据 '+c.update+' 条。','mt-import-stats'));
  if(!c.valid)status.append(el('p','没有有效数据可写入，请修正文件后重新导入。','muted'));}
 if(mtImport.result){const c=mtImport.result.counts;
  status.append(el('p','导入数据 '+c.total+' 条，有效数据 '+c.valid+' 条，无效数据 '+c.invalid+' 条。其中新增数据 '+c.inserted+' 条，更新数据 '+c.updated+' 条。','mt-import-stats'));
  status.append(el('p',mtImport.result.phase==='completed'?'全部有效数据已写入。':'处理异常或中断，请下载标注结果核对已完成及待核对的数据。','muted'));}}
async function fetchMaintainHistory(){const request=++mtHistoryVersion,project=mtProject;mtHistory={items:[],loading:true,error:''};render();
 try{const params=new URLSearchParams({project_id:String(project),metric:mtHistoryFilter.metric});if(mtHistoryFilter.category)params.set('category_id',mtHistoryFilter.category);if(mtHistoryFilter.stat_date)params.set('stat_date',mtHistoryFilter.stat_date);if(mtHistoryFilter.source)params.set('source',mtHistoryFilter.source);const data=await api('/maintain/history?'+params);if(request!==mtHistoryVersion||project!==mtProject)return;mtHistory={items:data.items,loading:false,error:''};}
 catch(e){if(request!==mtHistoryVersion)return;mtHistory={items:[],loading:false,error:e.message};}render();}
function renderMaintainAux(target){const card=el('section',undefined,'card');target.append(card);
 card.append(el('h2','修改记录'));
 const form=el('form',undefined,'metric-search mt-history-search');form.setAttribute('aria-label','修改记录查询');
 const catField=el('div',undefined,'metric-search-field');const catLabel=el('label','指标类型');catLabel.htmlFor='mtHistCategory';
 const category=el('select');category.id='mtHistCategory';const all=el('option','全部类型');all.value='';category.append(all);for(const c of mtBoot.categories){const o=el('option',c.name);o.value=c.id;category.append(o);}category.value=mtHistoryFilter.category;catField.append(catLabel,category);
 const dateField=el('div',undefined,'metric-search-field');const dateLabel=el('label','统计日期');dateLabel.htmlFor='mtHistDate';
 const date=el('input');date.id='mtHistDate';date.type='date';date.value=mtHistoryFilter.stat_date;dateField.append(dateLabel,date);
 const srcField=el('div',undefined,'metric-search-field');const srcLabel=el('label','来源');srcLabel.htmlFor='mtHistSource';
 const source=el('select');source.id='mtHistSource';[['','全部来源'],['MANUAL','手工录入'],['CSV','CSV 导入'],['EXCEL','Excel 导入']].forEach(([v,t])=>{const o=el('option',t);o.value=v;source.append(o);});source.value=mtHistoryFilter.source;srcField.append(srcLabel,source);
 const nameField=el('div',undefined,'metric-search-field mt-history-name');const nameLabel=el('label','指标名称');nameLabel.htmlFor='mtHistName';
 const name=el('input');name.id='mtHistName';name.type='text';name.placeholder='请输入指标名称，支持模糊查询';name.maxLength=100;name.value=mtHistoryFilter.metric;nameField.append(nameLabel,name);
 const actions=el('div',undefined,'metric-search-actions');const query=el('button','查询','primary');query.type='submit';const reset=el('button','重置','secondary');reset.type='button';
 form.onsubmit=e=>{e.preventDefault();mtHistoryFilter={category:category.value,stat_date:date.value,source:source.value,metric:name.value.trim()};listPages.history.page=1;fetchMaintainHistory();};
 reset.addEventListener('click',()=>{category.value='';date.value='';source.value='';name.value='';mtHistoryFilter={category:'',stat_date:'',source:'',metric:''};listPages.history.page=1;fetchMaintainHistory();});
 actions.append(query,reset);form.append(catField,dateField,srcField,nameField,actions);card.append(form);
 if(!mtHistory){card.append(el('p','点击查询加载记录'));return;}if(mtHistory.error){card.append(el('p',mtHistory.error,'form-error'));return;}
 if(mtHistory.loading){card.append(el('p','正在加载…'));return;}
 const matched=mtHistory.items;listPages.history.total=matched.length;listPages.history.page=Math.max(1,Math.min(listPages.history.page,Math.max(1,Math.ceil(matched.length/listPages.history.size))));
 card.append(el('p',`共 ${matched.length} 条修改记录`,'metric-search-count'));
 if(!matched.length)card.append(el('p','当前条件下暂无修改记录。历史记录若无法安全确定项目归属，不向项目用户展示。','muted'));
 if(matched.length){const rows=pagedList('history',matched);const wrap=el('div',undefined,'table-wrap'),table=el('table');const head=el('tr');['保存时间（北京时间）','统计日期','指标','修改前','修改后','操作人','来源'].forEach(t=>head.append(el('th',t)));table.append(head);
 for(const r of rows){const row=el('tr'),time=new Date(/[Zz]|[+-]\d\d:\d\d$/.test(r.saved_at)?r.saved_at:r.saved_at+'Z').toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});[time,r.stat_date,r.metric,r.before??'未维护',r.after??'已清空',r.operator,r.source].forEach(v=>row.append(el('td',String(v))));table.append(row);}wrap.append(table);card.append(wrap);}
 card.append(buildPager('history','修改记录'));
}
