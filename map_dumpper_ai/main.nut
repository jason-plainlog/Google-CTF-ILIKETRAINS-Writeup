class TestAI extends AIController{
  constructor(){} 
}
 
function TestAI::Start(){
  AILog.Info("TestAI Started.");

  // 1220 * 3742
  for(local x = 0; x < 1220; x++){
    for(local y = 0; y < 3742; y++){
      local p = (x << 12) + y;
        
      if(AIRail.IsRailTile(p)){
        AILog.Warning("rail (" + x + ", " + y + ", " + AIRail.GetRailTracks(p) + ")");
      }else if(AIBridge.IsBridgeTile(p)){
        local end = AIBridge.GetOtherBridgeEnd(p)
        AILog.Warning("bridge (" + x + ", " + y + ") to (" + (end >> 12) + ", " + (end % 4096) + ")");
      }
    }
  }
}
 
function TestAI::Save(){
  local table = {};	
  return table;
}
 
function TestAI::Load(version, data){
   AILog.Info(" Loaded");
}
 
function TestAI::SetCompanyName(){}